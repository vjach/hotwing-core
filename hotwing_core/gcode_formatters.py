from __future__ import division


class GcodeFormatterBase():
    """
    Gcode Formatter's job is to convert the commands maintained
    by the Gcode class and format them into the appropriate format
    for the specification of Gcode being generated.

    On any subclass, you are expected to implement at a minimum
    the _process_move and _process_fast_move commands.
    """
    def __init__(self, parent):
        self.parent = parent

    def _process_move(cls, command):
        raise NotImplementedError

    def _process_fast_move(cls, command):
        raise NotImplementedError

    def _start_commands():
        return []

    def _end_commands():
        return []


class DebugGcodeFormatter(GcodeFormatterBase):
    """
    This is meant as a debugging class.  It will output the commands
    as a line of text separated by tabs.
    """
    def _process_move(cls, command):
        return cls._move_to_string(command)

    def _process_fast_move(cls, command):
        return cls._move_to_string(command)

    def _move_to_string(cls, command):
        cmd_type = command[0]
        cmds_as_str = [cmd_type]
        for c in command[1]:
            type_ = type(c)
            if type_ is str:
                cmds_as_str.append(c)
            if type_ is int or type_ is float:
                cmds_as_str.append("%.10f" % c)
        return "\t".join(cmds_as_str)

    def _start_commands(self):
        out = []
        out.append("Units: %s" % self.parent.units)
        out.append("Feedrate: %s" % self.parent.feedrate)
        return out

    def _end_commands(self):
        return []


class GenericGcodeFormatter(GcodeFormatterBase):
    """
    Generic Gcode (RS-274?) formatter
    Made to work with LinuxCNC
    """
    def _process_move(cls, command):
        return "G1 x%.10f y%.10f u%.10f v%.10f" % command[1]

    def _process_fast_move(cls, command):
        return "G0 x%.10f y%.10f u%.10f v%.10f" % command[1]

    def _start_commands(self):
        out = []

        # Set feedrate
        out.append("F%s" % self.parent.feedrate)

        ## Working Plane
        out.append("G17") # is this necessary?

        # Units        
        if self.parent.units.lower() == "inches":
            out.append("G20")
        elif self.parent.units.lower() == "millimeters":
            out.append("G21")
        else:
            out.append("(Unknown units '%s' specified!)" % self.parent.units)

        ## Absolute Mode
        out.append("G90")

        # Control path mode
        # G64 - Set Blended Path Control Mode
        # Set path tolerance using P value
        if self.parent.units.lower() == "inches":
            out.append("G64 P%.6f" % (1.0/64) )
        elif self.parent.units.lower() == "millimeters":
            out.append("G64 P%.2f" % (0.5) )
        

        # Use first work offset
        out.append("G54")

        return out

    def _end_commands(self):
        out = []
        # End Program
        out.append("M30")
        return out


class GcodeFormatterFactory():
    formatters = [
                    GenericGcodeFormatter,
                    DebugGcodeFormatter
                 ]
    default = GenericGcodeFormatter

    @classmethod
    def get_cls(cls, name):
        """
        Get a cutting strategy by name

        Returns:
            GcodeFormatter object
        """
        name = name.lower()
        
        if name == "default":
            return cls.default

        for f in cls.formatters:
            f_name = f.__class__.__name__.lower()
            if f_name == name:
                return f

        logging.error("ERROR: GCODE FORMATTER NAME INCORRECT, FALLING BACK TO DEFAULT")
        return cls.default

