locals {
  environments = {
    prod = {
      put_metric_data_namespace = "home"

      sensors = {
        mechanical_room = {
          co = "031717010202"
        }
      }
    }
  }
}
