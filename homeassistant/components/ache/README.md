# ACH (Air Changes per Hour) Integration

This integration calculates Air Changes per Hour (ACH) by analyzing the exponential decay of CO2 or other gas sensor readings.

## Configuration

### YAML Configuration

Add the following to your `configuration.yaml`:

```yaml
ache:
  - source_sensor: sensor.living_room_co2
    room_volume: 50.0  # Room volume in m³
    min_r_squared: 0.85  # Optional, minimum R² for reliable estimates (default: 0.85)

  - source_sensor: sensor.bedroom_co2
    room_volume: 35.0
```

**Configuration Variables:**

- `source_sensor` (Required): Entity ID of the source sensor (typically a CO2 sensor)
- `room_volume` (Required): Room volume in cubic meters (m³), range: 1-1000
- `min_r_squared` (Optional): Minimum R² threshold for ACH estimates, range: 0.5-1.0, default: 0.85

### UI Configuration

Alternatively, configure via the UI:

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for **ache**
4. Follow the configuration steps

## How It Works

1. The integration monitors your configured gas sensor (e.g., CO2)
2. It detects decay sequences (when values decrease monotonically)
3. Fits an exponential decay curve to the data
4. Calculates ACH from the decay rate
5. Only displays ACH when the curve fit quality (R²) meets the threshold

## Sensor Attributes

When an ACH estimate is available, the sensor provides these attributes:

- `r_squared`: Goodness of fit (0-1, higher is better)
- `decay_rate`: Decay rate per second
- `baseline_ppm`: Baseline concentration level
- `initial_ppm`: Initial concentration at start of decay
- `data_points`: Number of data points used
- `room_volume_m3`: Configured room volume

When unavailable (insufficient data or poor fit quality):
- The sensor state shows "unavailable"
- No ACH value is displayed until a valid decay sequence is detected

## Requirements

- Python package: `scipy>=1.15.1` (automatically installed)
- A sensor that measures gas concentration (CO2, VOC, etc.)
- Minimum 5 consecutive decreasing readings for ACH calculation
