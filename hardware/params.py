"""Machine constants for the pen-plotter hardware models.

Everything dimensional that more than one part cares about lives here, so a
change propagates instead of being re-typed. Units are mm throughout, matching
the machine's G21 convention.

Values that mirror the README's machine table are marked [README]; keep the two
in sync.
"""

# ---------------------------------------------------------------------------
# Aluminium extrusion (20-series T-slot)
# ---------------------------------------------------------------------------

# Cross-section of the frame rails. 2040 = 20 mm x 40 mm.
PROFILE_W = 20.0   # in-plane width  (footprint the rail occupies on the table)
PROFILE_H = 40.0   # height, along Z (the tall direction, for bending stiffness)

# Lay the rails on their side instead: 40 mm footprint, 20 mm tall. Lower
# profile, less stiff over a 1 m span. Flip by swapping the two values above.

# 20-series T-slot geometry. Nominal for OpenBuilds / Misumi-style 20-series;
# vendors differ by a few tenths, so measure yours before cutting anything that
# has to slide in a slot.
SLOT_MOUTH_W = 6.2    # width of the slot opening at the outer face
SLOT_LIP_D   = 2.0    # depth of the parallel lip before the channel flares
SLOT_INNER_W = 11.5   # widest point of the channel, behind the lip
SLOT_FLARE_D = 2.8    # depth at which the channel reaches its widest
SLOT_ROOT_W  = 5.2    # width where the channel bottoms out
SLOT_DEPTH   = 6.0    # total depth of the slot from the outer face

# The channel narrows again towards its root (SLOT_INNER_W -> SLOT_ROOT_W).
# That taper is what leaves the diagonal webs joining each corner to the middle
# of the section. Widen the root and the corners detach from the core -- which
# is wrong geometry, and _assert_connected() in profiles.py will catch it.
BORE_D       = 4.2    # central bore per 20 mm cell (M5 self-tapping)
PROFILE_CHAMFER = 1.5 # outer corner chamfer

CELL = 20.0           # the 20 mm unit cell the series is built from

ALUMINIUM_DENSITY = 2.70e-3  # g/mm^3, for the mass estimate in make.py

# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------

# Outer envelope of the extrusion frame, in the table plane.
# Sized to the IKEA LINNMON 100 x 60 cm tabletop [README].
FRAME_OUTER_X = 1000.0
FRAME_OUTER_Y = 600.0

# Corner joinery. "butt" = the X rails run the full FRAME_OUTER_X and the Y
# rails fit between them (the usual arrangement with corner brackets or
# end-tapped M5s). "mitre" is not implemented yet.
FRAME_JOINT = "butt"

# Which pair runs full length. True = X rails full, Y rails cut short.
FRAME_LONG_RAILS_ALONG_X = True

# ---------------------------------------------------------------------------
# Machine envelope (from the README, for parts still to come)
# ---------------------------------------------------------------------------

USABLE_X = 150.0
USABLE_Y = 150.0
