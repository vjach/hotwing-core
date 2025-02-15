from __future__ import division
from .coordinate import Coordinate
from .surface import Surface
import re
import copy
import os
import sys
import logging
import ssl

try:
    # For Python 3.0 and later
    import urllib.request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen

logging.getLogger(__name__)


class Profile():
    """
    A Profile holds a representation of an airfoil, consisting of two Surface objects defining the top
    and bottom.  The job of the Profile is to load a profile depending on the input the user initialized
    it with and maintain the Surfaces.

    The Profile __init__ method can take a variety of different inputs using method overloading.

    Initialization Method Overloading:

        Profile(filepath):
            filepath: String-like object containing the file path to dat file to load

        Profile(url):
            url: String-like object containing a URL to the dat file to load

        Profile(coordinates)
            coordinates: List of Coordinate Objects to create Profile from

        Profile(top_surface, bottom_surface)
            top_surface: Surface - top surface to create Profile from
            bottom_surface: Surface - bottom surface to create Profile from

    :ivar top: Surface object that makes up the top of the Profile
    :ivar bottom: Surface object that makes up the bottom of the Profile
    """

    def __init__(self, *args):
        self.spar_center = None
        self.spar_radius = 0
        
        if len(args) == 1 and isinstance(args[0], list):
            # list of coordinates
            self.top, self.bottom = self._split_profile(args[0])
        elif len(args) == 1 and isinstance(args[0], str):
            if "http://" in args[0] or "https://" in args[0]:
                # received a URL
                self.top, self.bottom = self._load_dat_from_url(args[0])
            else:
                # received a filename
                self.top, self.bottom = self._load_dat_file(args[0])
        elif len(args) == 2 and isinstance(args[0], Surface) and isinstance(args[1], Surface):
            # received two surfaces
            self.top = args[0]
            self.bottom = args[1]
        else:
            raise AttributeError

    @property
    def x_bounds(self):
        """
        Get the min and max X values in the Profile.

        Returns:
            Tuple of Floats: (min_x,max_x) - containing the min and max X values in the profile.
        """
        min_x = min((self.bottom.left.x, self.top.left.x))
        max_x = max((self.bottom.right.x, self.top.right.x))
        return (min_x, max_x)

    @property
    def y_bounds(self):
        """
        Get the min and max Y values in the Profile.

        Returns:
            Tuple of Floats: (min_y,max_y) - containing the min and max y values in the profile.
        """
        top_min, top_max = self.top.bounds
        bottom_min, bottom_max = self.bottom.bounds
        min_y = min((top_min.y, bottom_min.y))
        max_y = max((top_max.y, bottom_max.y))
        return (min_y, max_y)

    @property
    def left_midpoint(self):
        """
        Find an XY position at the left-most value of the Profile half way vertically between the two Surfaces

        1) Finds the X value for the leftmost point in the Profile
        2) Finds/Interpolates the Coordinates on the top and bottom Surfaces for X
        3) Finds the point in between the Coordinates, which is a coordinate vertically mid-way
            between the points

        Returns:
            Coordinate:
        """
        min_x, max_x = self.x_bounds
        top_c = self.top.interpolate(min_x)
        bottom_c = self.bottom.interpolate(min_x)
        average_y = (top_c.y + bottom_c.y) / 2
        return Coordinate(min_x, average_y)

    @property
    def right_midpoint(self):
        """
        Find a XY position at the right-most value of the Profile half way between vertically the two Surfaces

        1) Finds the X value for the right most point in the Profile
        2) Finds/Interpolates the Coordinates on the top and bottom Surfaces for X
        3) Finds the point in between the Coordinates, which is a coordinate vertically mid-way
            between the points

        Returns:
            Coordinate:
        """
        min_x, max_x = self.x_bounds

        top_c = self.top.interpolate(max_x)
        bottom_c = self.bottom.interpolate(max_x)
        average_y = (top_c.y + bottom_c.y) / 2
        return Coordinate(max_x, average_y)

    def set_spar(self, center, radius):
        self.spar_center = center
        self.spar_radius = radius

    @classmethod
    def rotate(cls, origin, profile, angle):
        """
        Rotate a Profile around a point.

        Args:
            origin (Coordinate): object that defines the point to rotate profile around
            profile (Profile): object to rotate
            angle (Float): degrees to rotate profile.

        Returns:
            Profile: New rotated Profile
        """
        top_coords = Surface.rotate(origin, profile.top, angle)
        bot_coords = Surface.rotate(origin, profile.bottom, angle)
        
        ret = cls(top_coords, bot_coords)
        ret.set_spar(Coordinate.rotate(origin, self.spar_center, angle), self.spar_radius)
        return ret

    @classmethod
    def copy(cls, profile):
        """
        Create a copy of a Profile

        Args:
            profile (Profile): object to copy

        Returns:
            Profile: new copied Profile object
        """
        top = profile.top
        bottom = profile.bottom
        ret = Profile(top, bottom)
        ret.set_spar(profile.spar_center, profile.spar_radius)
        return ret

    @classmethod
    def scale(cls, profile, scale):
        """
        Scale a Profile

        Delagates to the Surface objects' scale method

        Args:
            profile (Profile): object to scale
            scale (Float): - value to scale profile by.  Value of 1 will produce no effect; 2 will double 
                             the size; 0.5 will reduce to half the size.

        Returns:
            Profile: new scaled Profile
        """
        top = Surface.scale(profile.top, scale)
        bottom = Surface.scale(profile.bottom, scale)
        ret = Profile(top, bottom)
        ret.set_spar(profile.spar_center, profile.spar_radius)
        return ret


    @classmethod
    def translate(cls, profile, offset):
        """
        Offset a Profile left, right, up or down.

        Delagates to the Surface objects' translate method

        Args:
            profile (Profile): object to offset
            offset (Coordinate): - Amount to offset the Profile in the x and y directions - this value is 
                    simply added to each of the coordinates in the Profile's Surfaces.

        Returns:
            Profile: new offset Profile
        """
        top = Surface.translate(profile.top, offset)
        bottom = Surface.translate(profile.bottom, offset)
        ret =  Profile(top, bottom)
        ret.set_spar(Coordinate.translate(profile.spar_center, offset), profile.spar_radius)
        return ret

    @classmethod
    def offset_around_profile(cls, profile, top_offset, bottom_offset):
        """
        Offset each of a Profile's Surfaces around itself. It can be thought of as scaling the Profile's
        Surfaces inward or outward around the Surfaces.

        Delagates to the Surface objects' offset_around_surface method

        Args:
            profile (Profile): object to offset
            top_offset    (Float): -  Positive value expands profile (offsets upwards/outwards),
                                    negative value contracs profile (offsets downwards/inwards).
            bottom_offset (Float): -  Positive value expands profile (offsets downwards/outwards),
                                    negative value contracs profile (offsets upwards/inwards).

        Returns:
            Profile: new offset Profile
        """
        top = Surface.offset_around_surface(profile.top, top_offset)
        bottom = Surface.offset_around_surface(profile.bottom, -bottom_offset)
        ret = Profile(top, bottom)
        ret.set_spar(profile.spar_center, profile.spar_radius)
        return ret

    @classmethod
    def trim(cls, profile, x_min=None, x_max=None):
        """
        Trim a Profile's Surfaces to new starting and ending x values.

        IMPORTANT - If you specify a value smaller than the min or larger than the max, by default
        those values will be interpolated and may actually make the width of the surface larger.

        Delagates trim to the Surface objects

        Args:
            profile (Profile): object to trim
            x_min (Float): left-most value to trim the profile to.
            x_max (Float): right-most value to trim the profile to.

        Returns:
            Profile - new trimmed Profile
        """
        top = Surface.trim(profile.top, x_min, x_max)
        bottom = Surface.trim(profile.bottom, x_min, x_max)
        ret = Profile(top, bottom)
        ret.set_spar(profile.spar_center, profile.spar_radius)
        return ret

    @classmethod
    def trim_overlap(cls, profile):
        """
        Trims a Profiles Surfaces where they overlap.

        After manipulating Surfaces, the profiles may now overlap.  This method finds this point
        using the class' _find_convergence_points method and then trims the profiles based on the
        results.  If no over lap(s) is/are found, not trimming will occur.

        Args:
            profile (Profile): object to trim.

        Returns:
            Profile: new trimmed Profile
        """
        x1, x2 = profile._find_convergence_points()
        if x1 is None:
            x1 = profile.x_bounds[0]
        if x2 is None:
            x2 = profile.x_bounds[1]
        obj = cls.trim(profile, x1, x2)
        return obj

    @classmethod
    def interpolate_new_profile(
            cls, p1, p2, dist_between, dist_interp, points=200):
        """
        Create a new Profile interpolated from two other Profiles.

        Delagates to the Surface objects.

        Args:
            p1 (Profile): first profile to interpolate from
            p2 (Profile): second profile to interpolate from
            dist_between (Float): Distance between profiles
            dist_interp (Float): Distance from s1 where new profile should be interpolated
            points (Int): Number of points to use for interpolating each surface of the profile

        Returns:
            Profile: New Profile interpolated from s1 and s2
        """
        top = Surface.interpolate_new_surface(
            p1.top, p2.top, dist_between, dist_interp, points)
        bot = Surface.interpolate_new_surface(
            p1.bottom, p2.bottom, dist_between, dist_interp, points)
        ret = Profile(top, bot)
        ret.set_spar(profile.spar_center, profile.spar_radius)
        return ret

    def _load_dat_file(self, f):
        """
        Read the contents of a Selig-formatted file and loads the coordinates into the Class'
        coordinates attribute.

        Args:
            f (String):String-like object containing the file path to a Selig-formatted file.

        Returns:
            Tuple of (two) Profiles : (top_profile, bottom_profile)
        """
        coordinates = []
        with open(f, "r") as f:
            for line in f.readlines():
                c = self._parse_dat_file_line(line)
                if c:
                    coordinates.append(c)
        self.all_coordinates = coordinates
        return self._split_profile(coordinates)

    def _load_dat_from_url(self, url):
        """
        Download the contents of a Selig-formatted file and loads the coordinates into 
        the Class' coordinates attribute.

        Args:
            f (String): String-like object containing a URL to the Selig-formatted.  Make sure you
               include http:// or https:// in the URL

        Returns:
            Tuple of (two) Profiles : (top_profile, bottom_profile)
        """

        if "urllib.request" in sys.modules:
            gcontext = ssl.SSLContext()
            req = urllib.request.Request(url)
            res = urllib.request.urlopen(req, context=gcontext)
            contents = res.read().decode('utf-8')
        else:
            # Python 2
            r = urlopen(url)
            contents = r.read()

        coordinates = []
        for line in contents.splitlines():
            c = self._parse_dat_file_line(line)
            if c:
                coordinates.append(c)
        self.all_coordinates = coordinates
        return self._split_profile(coordinates)

    def _parse_dat_file_line(self, line):
        """
        Take a single line for a dat file and parse out any coordinates
        """
        p = re.compile("^\s*(-*\d*\.\d*)\s*(-*\d*\.\d*)")
        m = p.match(line)
        if m:
            try:
                x = float(m.group(1))
                y = float(m.group(2))
            except ValueError:
                # error converting to float - ignore this line
                return None
            if x > 1 and y > 1:
                # the Lednicer format specifies the coord count - ignore this
                return None
            c =  Coordinate(x,y)
            return c
        return None

    def _split_profile(self, coordinates):
        """
        Split the coordinates into top and bottom surfaces

        Args:
            coordinates (Coordinates[]): list of coordinates

        Returns:
            Tuple of (two) Profiles : (top_profile, bottom_profile)
        """

        # determine direction
        inc_count = 0
        dec_count = 0
        # test the x direction of the first 5 coordinates
        for i in range(4):
            c1 = coordinates[i]
            c2 = coordinates[i+1]
            if c2.x > c1.x:
                inc_count += 1
            else:
                dec_count += 1

        if inc_count > dec_count:
            # get rightmost point
            max_x = max([c.x for c in coordinates])
            for i, c in enumerate(coordinates):
                if c.x == max_x:
                    coordinate_to_split_on = i
                    break
            top = coordinates[:coordinate_to_split_on + 1]
            bottom = coordinates[coordinate_to_split_on+1:]
        else:
            # get leftmost point
            min_x = min([c.x for c in coordinates])
            for i, c in enumerate(coordinates):
                if c.x == min_x:
                    coordinate_to_split_on = i
                    break
            top = coordinates[:coordinate_to_split_on + 1]
            bottom = coordinates[coordinate_to_split_on:]

        # coordinate_to_split_on = len(coordinates)
        # for i,c in enumerate(coordinates):
        #   if c.y < 0:
        #       coordinate_to_split_on = i
        #       break

        return (Surface(top), Surface(bottom))

    def _find_convergence_points(self):
        """
        Find convergence points of a Class' Profiles.

        Searches for convergence points from the middle of the profile to the left bound and then
        the middle of the profile to the right bound.  Uses the Class' _find_convergence_point
        method to perform the search.

        Returns:
            Tuple of Floats:  ex: (0.23,0.92), (0.23,None), (None,0.92), (None,None)
        """
        left_bound, right_bound = self.x_bounds
        midpoint = (left_bound + right_bound) / 2

        left = self._find_convergence_point(midpoint, left_bound)
        right = self._find_convergence_point(midpoint, right_bound)
        if left == right:
            return None, None
        return left, right

    def _find_convergence_point(self, x_start, x_stop, accuracy=0.000001):
        """
        Finds convergence points of a Class' Profiles between two x positions.

        Starts looking for convergence at the x_start value, then moves towards x_stop value until
        it finds a convergence point or hits the x_stop value.  Continues interating each found
        region and increasing the accuracy until the accuracy level is satisfied.

        Args:
            x_start (Float):
            x_end (Float):
            accuracy (Float): minimum level of error we can tolerate on the convergence.  The
                              algorithm doesn't solve for an exact value but can get very close
                              by iteration.  Set this value very high for more accuracy.

        Returns:
            Float: None if no convergence found
        """
        direction = "left" if x_start > x_stop else "right"

        # iterate until we get the accuracy we need
        for i in range(100):

            # set resolution to 1/100th of the search distance
            resolution = abs(x_start - x_stop) / 100
            region = self._find_region_of_convergence(x_start=x_start,
                                                      x_stop=x_stop,
                                                      resolution=resolution)
            if region is None:
                return None

            if abs(region[0] - region[1]) < accuracy:
                # accuracy is at a level we are happy with, return average of
                # ranges
                return (region[0] + region[1]) / 2

            if direction == "left":
                x_stop = region[0]
                x_start = region[1]
            else:
                x_start = region[0]
                x_stop = region[1]

    def _find_region_of_convergence(self, x_start, x_stop, resolution):
        """
        Finds a region of convergence for the Profile's Surfaces.

        Starting from the x_start and moving towards x_stop in increments defined by the resolution
        variable, we try to determine a range - between x and x-1 - where the surfaces cross over
        one other.

        Args:
            x_start (Float)
            x_stop (Float)
            resolution (Float)

        Returns:
            Tuple of Floats: (x1,x2) - two values that contain two x coordinates that bound the
                                       region between where the convergence occurs.  None if no
                                       convergence found.
        """
        x_val = x_start
        last_x = x_val
        if x_stop < x_start:
            while x_val > x_stop:
                t = self.top.interpolate(x_val)
                b = self.bottom.interpolate(x_val)
                if t.y - b.y < 0:
                    return (x_val, last_x)
                last_x = x_val
                x_val -= resolution
        else:
            while x_val < x_stop:
                t = self.top.interpolate(x_val)
                b = self.bottom.interpolate(x_val)
                if t.y - b.y < 0:
                    return (last_x, x_val)
                last_x = x_val
                x_val += resolution

        # couldn't find
        return None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if not self.top == other.top:
                return False
            elif not self.bottom == other.bottom:
                return False
            return True
        raise NotImplementedError

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        raise NotImplementedError

    def __add__(self, other):
        if isinstance(other, Coordinate):
            return Profile.translate(self,other)
        raise NotImplementedError

    def __sub__(self, other):
        if isinstance(other, Coordinate):
            new_coord = Coordinate(-other.x,-other.y)
            return Profile.translate(self,new_coord)
        raise NotImplementedError

    def __mul__(self, other):
        return Profile.scale(self, other)
