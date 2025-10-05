"""Constants for the ache integration."""

DOMAIN = "ache"

CONF_SOURCE_SENSOR = "source_sensor"
CONF_ROOM_VOLUME = "room_volume"
CONF_MIN_R_SQUARED = "min_r_squared"
CONF_BASELINE_CO2 = "baseline_co2"

# Default minimum R² threshold for reliable ACH estimates
DEFAULT_MIN_R_SQUARED = 0.85

# Default baseline CO2 level (outdoor air, in ppm)
DEFAULT_BASELINE_CO2 = 420.0

# Minimum number of decay points needed for fitting
MIN_DECAY_POINTS = 5
