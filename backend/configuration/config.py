# This is the API configuration file for backend REST API server for Django

# Flag to check for Postgre connection TRUE or FALSE
CHECKPOSTGRECONNECTION = 'TRUE'

BUFFER_RANGE = 10


# This is the API configuration file for backend REST API server for Django

# For Postgre database connection properties
#===============================================================
POSTGRE_USER = 'postgres2'
POSTGRE_PASSWORD = 'postgres2'
POSTGRE_HOST = '2.80.83.4'
POSTGRE_PORT = '5555'
POSTGRE_DATABASE = 'cm'
#===============================================================

# For HiveServer2 connection properties
#===============================================================
HIVE_USER = 'spark'
HIVE_PASSWORD = 'Pscada_STE123'
HIVE_HOST = '2.80.83.6'
HIVE_PORT = 10016
HIVE_DATABASE = 'cm'
#===============================================================

# ======================== HIVE PRODUCTION TABLES ===============================

# Dynamic tables
TRANSFORMER = 'transformer'
TRANSFORMER_LOADING = 'transformer_loading'
PARTIAL_DISCHARGE_MONITOR = 'partial_discharge_monitor'
DISSOLVED_GAS_ANALYSIS_GAS_MEASUREMENT = 'dissolved_gas_analysis_gas_measurement'
BATTERY_MONITORING_UNIT_STATION_BATTERY = 'battery_monitoring_unit_station_battery'
SWITCHGEAR_COUNTS = 'switchgear_counts'
SWITCHGEAR_TEMP_RES = 'switchgear_temp_res'
DOUBLE_CONVERTER = 'double_converter'
RECTIFIER = 'rectifier'
INVERTER = 'inverter'

# ======================== POSTGRESQL PRODUCTION TABLES ===============================

# Dynamic tables
WARNING_LOGS = 'warning_logs'
OPERATING_COUNT = 'operating_count'
TRANSFORMER_DATA = 'transformer_data'
SWITCHGEAR_DATA = 'switchgear_data'
DOUBLECONVERTER_DATA = 'doubleconverter_data'
DOUBLECONVERTER_OPERATIONAL_TIME = 'doubleconverter_operational_time'
RECTIFIER_DATA = 'rectifier_data'
INVERTER_DATA = 'inverter_data'
PREDICTION_MODEL = 'prediction_model'
PREDICTION_MODEL_INFO = 'prediction_model_info'

# Static tables
EQUIPMENT_INFO = 'equipment_info'
STATION_INFO = 'station_info'
TRANSFORMER_THRESHOLD = 'transformer_threshold'
TRANSFORMER_RANGE = 'transformer_range'
SWITCHGEAR_THRESHOLD = 'switchgear_threshold'
SWITCHGEAR_RANGE = 'switchgear_range'
DOUBLECONVERTER_THRESHOLD = 'doubleconverter_threshold'
DOUBLECONVERTER_RANGE = 'doubleconverter_range'
RECTIFIER_THRESHOLD = 'rectifier_threshold'
RECTIFIER_RANGE = 'rectifier_range'
INVERTER_THRESHOLD = 'inverter_threshold'
INVERTER_RANGE = 'inverter_range'
PDM_RANGE = 'pdm_range'
WARNING_DEF = 'warning_def'
OPERATOR_ID_PASSWORD = 'operator_id_password'

# ======================== equipment_type variables ================================

# Transformer
INTAKE_TRANSFORMER = 'MT'
SERVICE_TRANSFORMER_1MVA = 'ST_1MVA'
SERVICE_TRANSFORMER_26MVA = 'ST_2.6MVA'
RECTIFIER_TRANSFORMER = 'RT'
DOUBLE_CONVERTER_TRANSFORMER = 'DCT'
INVERTER_TRANSFORMER = 'IT'

TRANSFORMER_66KV = '66KV'
TRANSFORMER_22KV = '22KV'

# Transformer loading
PROTECTION_RELAY_PANEL_66KV = '66KV PROTECTION RELAY PANEL'

# Switchgear
SWITCHGEAR_66KV = '66KV'
SWITCHGEAR_22KV = '22KV'
SWITCHGEAR_750VDC = '750VDC'

# Double Converter
DOUBLECONVERTER_DCONVERTER = 'dconverter'

# Rectifier
RECTIFIER_RECTIFIER = 'rectifier'

# Inverter
INVERTER_INVERTER = 'inverter'

# ===========================Severity levels========================================
SEVERITY_CRITICAL = 4
SEVERITY_URGENT = 3
SEVERITY_MAJOR = 2
SEVERITY_MINOR = 1
# ============================Logging Modes========================================
INFO = 'INFO'
DEBUG = 'DEBUG'
WARNING = 'WARNING'
ERROR = 'ERROR'
ALERT = 'ALERT'

INFO_MODE = 'ON'
DEBUG_MODE = 'OFF'
WARNING_MODE = 'ON'
ERROR_MODE = 'ON'
ALERT_MODE = 'ON'
# ============================PDM configs==========================================

PDM_CHANNEL_1 = '-01'
PDM_CHANNEL_2 = '-02'
PDM_CHANNEL_3 = '-03'
PDM_CHANNEL_4 = '-04'
PDM_CHANNEL_5 = '-05'
PDM_CHANNEL_6 = '-06'

# ==================================================================================


