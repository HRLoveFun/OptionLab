# Shared utilities package.
# Modules:
#   constants      – domain-wide defaults (DEFAULT_*, FREQUENCY_DISPLAY)
#   date_helpers   – parse_month_str, exclusive_month_end, DateHelper
#   network        – init_yf_proxy, yf_throttle
#   formatters     – DataFormatter
#   api_errors     – ApiError + Flask error handlers
#   data_utils     – small numeric helpers
#   ticker_utils   – Yahoo ↔ Futu ticker normalisation
#   render_helpers – streaming slice renderers
