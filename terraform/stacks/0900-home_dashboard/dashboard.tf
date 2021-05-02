locals {
  dashboard_body = {
    widgets = [
      {
        type = "metric"

        x      = 0
        y      = 0
        width  = 24
        height = 6

        properties = {
          metrics = [
            [{
              expression = "m1 / 1000",
              label      = "Mechanical Room",
              id         = "e1"
              region     = "us-east-1"
              color      = "#2ca02c"
            }],
            [
              "home", "COConcentrationPPB", "SensorID", data.terraform_remote_state.air_quality.outputs.sensors.mechanical_room.co,
              {
                id      = "m1"
                color   = "#2ca02c"
                label   = "CO Concentration PPB - Mechanical Room"
                visible = false
              }
            ]
          ],
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          stat    = "Average"
          period  = 60
          yAxis = {
            left = {
              label     = "PPM"
              showUnits = false
              min       = 0
              max       = 100
            },
            right = {
              showUnits = false
            }
          }
          annotations = {
            horizontal = [
              {
                color = "#d62728"
                value = 30
              },
              {
                color = "#ffbb78"
                value = 10
              },
            ]
          },
          title = "CO Concentration"
        }
      }
    ]
  }
}

resource "aws_cloudwatch_dashboard" "home" {
  dashboard_name = local.env.dashboard_name
  dashboard_body = jsonencode(local.dashboard_body)
}
