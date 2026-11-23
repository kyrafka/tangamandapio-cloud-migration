moved {
  from = azurerm_service_plan.function
  to   = azurerm_service_plan.function[0]
}

moved {
  from = azurerm_linux_function_app.wms
  to   = azurerm_linux_function_app.wms[0]
}

moved {
  from = azurerm_role_assignment.function_package_reader
  to   = azurerm_role_assignment.function_package_reader[0]
}

moved {
  from = azurerm_role_assignment.function_blob
  to   = azurerm_role_assignment.function_blob[0]
}

moved {
  from = azurerm_role_assignment.function_queue
  to   = azurerm_role_assignment.function_queue[0]
}

moved {
  from = azurerm_role_assignment.function_poison_queue_reader
  to   = azurerm_role_assignment.function_poison_queue_reader[0]
}

moved {
  from = azurerm_monitor_metric_alert.function_http_5xx
  to   = azurerm_monitor_metric_alert.function_http_5xx[0]
}

moved {
  from = azurerm_monitor_metric_alert.function_latency
  to   = azurerm_monitor_metric_alert.function_latency[0]
}
