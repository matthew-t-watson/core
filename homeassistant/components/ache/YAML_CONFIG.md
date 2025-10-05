# YAML Configuration Examples

The ACH integration now supports both UI and YAML configuration.

## Basic YAML Configuration

Add to your `configuration.yaml`:

```yaml
ache:
  - source_sensor: sensor.living_room_co2
    room_volume: 50.0
```

## Full Configuration with All Options

```yaml
ache:
  - source_sensor: sensor.living_room_co2
    room_volume: 50.0
    min_r_squared: 0.85
```

## Multiple Rooms

You can monitor ACH for multiple rooms:

```yaml
ache:
  - source_sensor: sensor.living_room_co2
    room_volume: 50.0
    min_r_squared: 0.85

  - source_sensor: sensor.bedroom_co2
    room_volume: 35.0
    min_r_squared: 0.9

  - source_sensor: sensor.kitchen_co2
    room_volume: 42.0
```

## Configuration Options

| Option | Required | Type | Range | Default | Description |
|--------|----------|------|-------|---------|-------------|
| `source_sensor` | Yes | entity_id | - | - | Entity ID of CO2 or gas sensor |
| `room_volume` | Yes | float | 1.0 - 1000.0 | - | Room volume in cubic meters (m³) |
| `min_r_squared` | No | float | 0.5 - 1.0 | 0.85 | Minimum R² threshold for reliable estimates |

## After Configuration

1. Save `configuration.yaml`
2. Restart Home Assistant
3. The integration will automatically create config entries
4. Find your ACH sensors in the UI

## Sensor Entity

Each configuration creates a sensor with entity ID:
- `sensor.ach` (for single configuration)
- Additional sensors numbered sequentially for multiple configurations

## Switching Between YAML and UI

- **YAML to UI**: Existing YAML configurations will be imported as config entries on restart
- **Duplicates**: If you configure the same sensor in both YAML and UI, the YAML import will be skipped
- **Removal**: To remove a YAML-configured integration, delete it from `configuration.yaml` AND remove the config entry from the UI

## Example Automation

```yaml
automation:
  - alias: "Alert when ventilation is poor"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ach
        below: 0.5
        for:
          minutes: 15
    action:
      - service: notify.mobile_app
        data:
          message: "Living room ventilation is poor. ACH: {{ states('sensor.ach') }}"
```
