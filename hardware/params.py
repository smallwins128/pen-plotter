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
# Table (the bench the whole machine stands on)
# ---------------------------------------------------------------------------

# 5 ft along its length. The depth is taken as a round 600 mm to match the
# machine; a true 2 ft is 609.6 mm, which would leave ~5 mm each side.
TABLE_X = 1524.0
TABLE_Y = 600.0
TABLE_T = 18.0

# The machine sits hard against the left end, leaving the rest of the top clear
# for the electronics. Only the top is modelled -- legs are not, since nothing
# is mounted to them.
TABLE_MACHINE_AT_LEFT = True

# ---------------------------------------------------------------------------
# Base deck (the sheet the paper sits on)
# ---------------------------------------------------------------------------

# A steel sheet across the whole frame footprint, laid on the tabletop with the
# frame bolted down on top of it. It is NOT a spanning panel -- see deck.py for
# why. The tabletop carries it; the sheet just gives a hard, uniform surface.
DECK_T = 1.5
DECK_X = 1000.0       # full frame footprint, so the frame sits on it
DECK_Y = 600.0

DECK_HOLE_D = 5.5     # M5 clearance, into drop-in T-nuts in the rails' bottom slot
DECK_HOLE_PITCH = 160.0   # target spacing; actual is evened out to fit
DECK_EDGE_MARGIN = 70.0   # keep the end holes clear of the corner joints

# Everything above the deck is lifted by its thickness, so the frame sits on
# the sheet rather than intersecting it.
FRAME_BASE_Z = DECK_T

STEEL_DENSITY = 7.85e-3   # g/mm^3
STEEL_E = 200000.0        # N/mm^2
STEEL_NU = 0.30

# ---------------------------------------------------------------------------
# Cross bar (the moving gantry beam)
# ---------------------------------------------------------------------------

# The bar spans Y and travels along X, riding the two 1000 mm frame rails on
# OpenBuilds gantry plates.
CROSS_BAR_LEN = 700.0
CROSS_BAR_W = 20.0    # 2020
CROSS_BAR_H = 20.0

# Height of the underside of the cross bar above the top of the frame rails --
# i.e. the gantry plate + wheel stack.
#
# APPROXIMATE: eyeballed at 1-2 cm, taken as the midpoint. Good enough to lay
# the machine out; not good enough to drill against. Every Z dimension above
# the frame scales with it, so re-measure before committing to any part whose
# height has to be right (the pen carriage and pen tip most of all).
GANTRY_RISE = 15.0

# Gantry plate footprint along the direction of travel (X). Sets how much of
# the 1000 mm rail is lost to the plate. From the plate drawing: 65.5 mm square,
# 3 mm thick, R3 corners, 12x 5.10 and 3x 7.20 holes.
GANTRY_PLATE_LEN = 65.5

# Where to park the bar when rendering. 0 = mid-travel.
CROSS_BAR_X = 0.0

# ---------------------------------------------------------------------------
# Electronics enclosure
# ---------------------------------------------------------------------------

# A separate extrusion box bolted alongside the machine (option B), not sharing
# a rail with it -- so either can be moved without dismantling the other.
#
# Stainless covers are not modelled yet. Neither is any wiring. Contents are
# stand-in blocks at their real outside dimensions, so the volumes and the
# clearances between them are honest even though the parts are not detailed.
ENC_X = 450.0
ENC_Y = 320.0
ENC_Z = 200.0
ENC_PROFILE = 20.0        # 2020 throughout

# Gap between the machine's right-hand rail and the enclosure's left face.
# They bolt together across this with plates, which are not modelled yet.
ENC_GAP = 10.0

# Components sit on the top face of the bottom frame rails.
ENC_FLOOR_Z = ENC_PROFILE

# ---------------------------------------------------------------------------
# Machine envelope (from the README, for parts still to come)
# ---------------------------------------------------------------------------

USABLE_X = 150.0
USABLE_Y = 150.0
