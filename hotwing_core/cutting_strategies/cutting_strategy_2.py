from __future__ import division
from ..profile import Profile
from ..coordinate import Coordinate
from .base import CuttingStrategyBase
import logging
import numpy as np

logging.getLogger(__name__)


class CuttingStrategy2(CuttingStrategyBase):
    """
    The first cutting strategy
    """
    def cut(self):
        m = self.machine
        dwell_time = 1
        le_offset = 1
        te_offset = 1

        # sheet profile
        profile1 = m.panel.left_rib.profile
        profile2 = m.panel.right_rib.profile

        # Offset profiles for Kerf Value
        profile1 = Profile.offset_around_profile(
            profile1, m.kerf[0], m.kerf[0])
        profile2 = Profile.offset_around_profile(
            profile2, m.kerf[1], m.kerf[1])

        # Trim the overlap
        # profile1 = Profile.trim_overlap(profile1)
        # profile2 = Profile.trim_overlap(profile2)

        # MOVE TO SAFE HEIGHT
        self._move_to_safe_height()

        # calc le offset pos
        pos = m.calculate_move(
                profile1.left_midpoint - Coordinate(le_offset, 0),
                profile2.left_midpoint- Coordinate(le_offset, 0))

        ## MOVE FAST HORIZONTALLY TO SPOT ABOVE LE OFFSET
        m.gc.fast_move( {'x':pos['x'],'u':pos['u']})

        ## MOVE DOWN TO JUST ABOVE FOAM
        m.gc.fast_move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )

        # CUT DOWN TO LEADING EDGE OFFSET
        m.gc.move(pos, ["do_not_normalize"])
        self.machine.gc.dwell(dwell_time)

        # CUT INWARDS TO LEADING EDGE
        m.gc.move(m.calculate_move(profile1.left_midpoint, profile2.left_midpoint))
        self.machine.gc.dwell(dwell_time)

        # CUT THE TOP PROFILE
        self._cut_top_profile(profile1, profile2, dwell_time)

        # CUT TO TRAILING EDGE AT MIDDLE OF PROFILE
        m.gc.move(
            m.calculate_move(
                profile1.right_midpoint,
                profile2.right_midpoint)
        )
        self.machine.gc.dwell(dwell_time)

        # CUT TO TRAILING EDGE OFFSET
        m.gc.move(
            m.calculate_move(
                profile1.right_midpoint + Coordinate(te_offset,0),
                profile2.right_midpoint + Coordinate(te_offset,0))
        )
        self.machine.gc.dwell(dwell_time)


        ## MOVE UP JUST ABOVE FOAM
        m.gc.move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )
        self._move_to_safe_height()
        ## MOVE FAST HORIZONTALLY TO SPOT ABOVE LE OFFSET
        m.gc.fast_move( {'x':pos['x'],'u':pos['u']} )
        m.gc.fast_move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )
        # CUT DOWN TO LEADING EDGE OFFSET (AGAIN)
        m.gc.move(pos)
        self.machine.gc.dwell(dwell_time)

        # CUT INWARDS TO LEADING EDGE
        m.gc.move(m.calculate_move(profile1.left_midpoint, profile2.left_midpoint))
        self.machine.gc.dwell(dwell_time)

        # CUT BOTTOM PROFILE
        self._cut_bottom_profile(profile1, profile2, dwell_time)
        # CUT TO TRAILING EDGE
        m.gc.move(m.calculate_move(profile1.right_midpoint, profile2.right_midpoint))

        # CUT TO TRAILING EDGE OFFSET
        m.gc.move(
            m.calculate_move(
                profile1.right_midpoint - Coordinate(te_offset,0),
                profile2.right_midpoint - Coordinate(te_offset,0))
        )
        self.machine.gc.dwell(dwell_time)

        # CUT UPWARD TO JUST ABOVE FOAM
        m.gc.move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )
        self.machine.gc.dwell(dwell_time*2)

        # MOVE TO SAFE HEIGHT
        self._move_to_safe_height()

        if m.panel.left_rib.tail_stock:
            # calculate position above tail stock
            r1_stock = m.panel.left_rib.tail_stock
            r2_stock = m.panel.right_rib.tail_stock
            
            ts_pos = m.calculate_move(
                Coordinate(profile1.right_midpoint.x - r1_stock + m.kerf[0],0),
                Coordinate(profile2.right_midpoint.x - r2_stock + m.kerf[1],0)
            )

            # MOVE HORIZONTALLY TO ABOVE TAIL STOCK
            m.gc.fast_move({'x':ts_pos['x'],'u':ts_pos['u']} )

            # MOVE DOWN TO JUST ABOVE FOAM
            m.gc.fast_move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )

            # CUT DOWN TO 0 HEIGHT
            m.gc.move( {'y':0,'v':0}, ["do_not_normalize"] )

            # CUT UP TO JUST ABOVE FOAM
            m.gc.move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )
            self.machine.gc.dwell(dwell_time*2)
            
            # MOVE UP TO SAFE HEIGHT
            self._move_to_safe_height()


        if m.panel.left_rib.front_stock:
            r1_stock = self.machine.panel.left_rib.front_stock
            r2_stock = self.machine.panel.right_rib.front_stock

            fs_pos = m.calculate_move(
                Coordinate(profile1.left_midpoint.x + r1_stock - m.kerf[0],0),
                Coordinate(profile2.left_midpoint.x + r2_stock - m.kerf[1],0)
            )

            # MOVE HORIZONTALLY TO ABOVE FRONT STOCK
            m.gc.fast_move({'x':fs_pos['x'],'u':fs_pos['u']} )

            # MOVE DOWN TO JUST ABOVE FOAM
            m.gc.fast_move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )

            # CUT DOWN TO 0 HEIGHT
            m.gc.move( {'y':0,'v':0}, ["do_not_normalize"] )

            # CUT UP TO JUST ABOVE FOAM
            m.gc.move( {'y':m.foam_height*1.1,'v':m.foam_height*1.1}, ["do_not_normalize"] )

            # MOVE UP TO SAFE HEIGHT
            self._move_to_safe_height()

        self._cut_spar(profile1, profile2, dwell_time)



    def _cut_top_profile(self, profile1, profile2, dwell_time):
        # cut top profile
        c1 = profile1.top.coordinates[0]
        c2 = profile2.top.coordinates[0]

        a_bounds_min, a_bounds_max = profile1.top.bounds
        b_bounds_min, b_bounds_max = profile2.top.bounds
        a_width = a_bounds_max.x - a_bounds_min.x
        b_width = b_bounds_max.x - b_bounds_min.x

        for i in range(self.machine.profile_points):
            if i == 0:
                self.machine.gc.dwell(dwell_time)
            pct = i / self.machine.profile_points
            c1 = profile1.top.interpolate_around_profile_dist_pct(pct)
            c2 = profile2.top.interpolate_around_profile_dist_pct(pct)
            self.machine.gc.move(self.machine.calculate_move(c1, c2))
            if i == 0:
                # dwell on first point
                self.machine.gc.dwell(dwell_time)

        # cut to last point
        self.machine.gc.move(self.machine.calculate_move(profile1.top.coordinates[-1],
                                                        profile2.top.coordinates[-1]))
        self.machine.gc.dwell(dwell_time)


    def _cut_bottom_profile(self, profile1, profile2, dwell_time):
        c1 = profile1.top.coordinates[0]
        c2 = profile2.top.coordinates[0]
        # cut bottom profile
        a_bounds_min, a_bounds_max = profile1.bottom.bounds
        b_bounds_min, b_bounds_max = profile2.bottom.bounds
        a_width = a_bounds_max.x - a_bounds_min.x
        b_width = b_bounds_max.x - b_bounds_min.x

        for i in range(self.machine.profile_points):
            pct = i / self.machine.profile_points
            c1 = profile1.bottom.interpolate_around_profile_dist_pct(pct)
            c2 = profile2.bottom.interpolate_around_profile_dist_pct(pct)
            self.machine.gc.move(self.machine.calculate_move(c1, c2))
            if i == 0:
                # dwell on first point
                self.machine.gc.dwell(dwell_time)

        # TODO: cut to last point

        self.machine.gc.dwell(dwell_time)

    def _cut_spar(self, profile1, profile2, dwell_time):
        spar1_center = np.array([profile1.spar_center.x, profile1.spar_center.y])
        spar2_center = np.array([profile2.spar_center.x, profile2.spar_center.y])
 
        self.machine.gc.fast_move( {'x':spar1_center[0] + profile1.spar_radius, 'y':self.machine.foam_height*1.1, 'u':spar2_center[0] + profile2.spar_radius, 'v':self.machine.foam_height*1.1})
        self.machine.gc.move(self.machine.calculate_move(Coordinate(*spar1_center), Coordinate(*spar2_center)))
        spar_points = 360
        for i in range(spar_points):
            c1 = spar1_center + profile1.spar_radius * np.array([np.cos(2 * np.pi * i / spar_points), np.sin(2 * np.pi * i / spar_points)])
            c2 = spar2_center + profile2.spar_radius * np.array([np.cos(2 * np.pi * i / spar_points), np.sin(2 * np.pi * i / spar_points)])
            c1 = Coordinate(*c1)
            c2 = Coordinate(*c2)
            self.machine.gc.move(self.machine.calculate_move(c1, c2))

        self.machine.gc.move(self.machine.calculate_move(Coordinate(*spar1_center), Coordinate(*spar2_center)))
