
from django.urls import path

# For main dashboard purposes
from backend.dashboard.stationViews import StationView

# For statistical purposes
from backend.statistics.predictiveMessagesViews import PredictiveMessagesView
from backend.statistics.statisticsViews import StatisticsView
from backend.statistics.warningCountViews import WarningCountView

# For equipment configurations
from backend.configuration.configurationViews import ConfigurationView
from backend.configuration.thresholdViews import ThresholdView
from backend.authentication.authenticationViews import AuthenticationView

# For transformers purposes
from backend.transformer.transformerViews import TransformerView
from backend.transformer.transformerWindingViews import TransformerWindingView
from backend.transformer.transformerLoadingViews import TransformerLoadingView
from backend.transformer.transformerReadingViews import TransformerReadingsView
from backend.transformer.transformerTrendingViews import TransformerTrendingsView
from backend.transformer.transformerKeyGasViews import TransformerKeyGasView
from backend.transformer.transformerDuvalTriangleViews import TransformerDuvalTriangleView
from backend.transformer.transformerPartialDischargeViews import TransformerPartialDischargeView

# For switchgears purposes
from backend.switchgear.switchgearViews import SwitchgearView
from backend.switchgear.circuitBreakerOperatingCounterViews import CircuitBreakerOperatingCounterView
from backend.switchgear.circuitBreakerInfoViews import CircuitBreakerInfoView
from backend.switchgear.switchgearTrendingViews import SwitchgearTrendingsView
from backend.switchgear.switchgearReadingViews import SwitchgearReadingsView
from backend.switchgear.switchgearPredictionViews import SwitchgearPredictionsView
from backend.switchgear.switchgearPartialDischargeViews import SwitchgearPartialDischargeView

# For doubleconverters purposes
from backend.doubleconverter.doubleconverterViews import DoubleconverterView
from backend.doubleconverter.doubleconverterReadingViews import DoubleconverterReadingsView
from backend.doubleconverter.doubleconverterTrendingViews import DoubleconverterTrendingsView
from backend.doubleconverter.operationCountsViews import OperationCountsView
from backend.doubleconverter.operationInfoViews import OperationInfoView
from backend.doubleconverter.operationTimeViews import OperationTimeView
from backend.doubleconverter.powerStatusViews import PowerStatusView
from backend.doubleconverter.coolingFanViews import CoolingFanView
from backend.doubleconverter.coolingFanInfoViews import CoolingFanInfoView
from backend.doubleconverter.elementTemperatureViews import ElementTemperatureView
from backend.doubleconverter.doubleconverterPredictionViews import DoubleconverterPredictionsView

# For rectifier purposes
from backend.rectifier.rectifierViews import RectifierView
from backend.rectifier.rectifierReadingViews import RectifierReadingsView
from backend.rectifier.rectifierTrendingViews import RectifierTrendingsView
from backend.rectifier.panelTemperatureViews import PanelTemperatureView

# For inverter purposes
from backend.inverter.inverterViews import InverterView
from backend.inverter.inverterReadingViews import InverterReadingsView
from backend.inverter.inverterTrendingViews import InverterTrendingsView
from backend.inverter.inverterPanelTemperatureViews import InverterPanelTemperatureView
from backend.inverter.numberOfOperationsViews import NumberOfOperationsView
from backend.inverter.maximumPowerViews import MaximumPowerView
from backend.inverter.inverterOperationInfoViews import InverterOperationInfoView

# To update the switchgear operating count(not in use anymore)
#from backend.updatecounter.updateCounter import UpdateCounter


urlpatterns = [

	#path('update-counter/',UpdateCounter.as_view(),name="update-counter"),

	path('predictive-messages',PredictiveMessagesView.as_view(),name="predictive-messages"),
	path('stations',StationView.as_view(),name="stations"),
	path('alarm-counts',WarningCountView.as_view(),name="alarm-counts"),
	path('statistics',StatisticsView.as_view(),name="statistics"),
	path('configurations',ConfigurationView.as_view(),name="configurations"),
	path('configurations/thresholds',ThresholdView.as_view(),name="configurations/thresholds"),
	path('user_authenticate',AuthenticationView.as_view(),name="user_authenticate"),
	
	path('transformers',TransformerView.as_view(),name="transformers"),
	path('transformers/winding-temperature',TransformerWindingView.as_view(),name="transformers/winding-temperature"),
	path('transformers/loading-status',TransformerLoadingView.as_view(),name="transformers/loading-status"),
	path('transformers/readings',TransformerReadingsView.as_view(),name="transformers/readings"),
	path('transformers/historical-trendings',TransformerTrendingsView.as_view(),name="transformers/historical-trendings"),
	path('transformers/key-gas',TransformerKeyGasView.as_view(),name="transformers/key-gas"),
	path('transformers/duval-triangle',TransformerDuvalTriangleView.as_view(),name="transformers/duval-triangle"),
	path('transformers/pdm-info',TransformerPartialDischargeView.as_view(),name="transformers/pdm-info"),
	
	path('switchgears',SwitchgearView.as_view(),name="switchgears"),
	path('switchgears/cb-operating-counters',CircuitBreakerOperatingCounterView.as_view(),name="switchgears/cb-operating-counters"),
	path('switchgears/cb-info',CircuitBreakerInfoView.as_view(),name="switchgears/cb-info"),
	path('switchgears/historical-trendings',SwitchgearTrendingsView.as_view(),name="switchgears/historical-trendings"),
	path('switchgears/prediction-models',SwitchgearPredictionsView.as_view(),name="switchgears/prediction-models"),
	path('switchgears/readings',SwitchgearReadingsView.as_view(),name="switchgears/readings"),
	path('switchgears/pdm-info',SwitchgearPartialDischargeView.as_view(),name="switchgears/pdm-info"),

	path('double-converters',DoubleconverterView.as_view(),name="double-converters"),
	path('double-converters/readings',DoubleconverterReadingsView.as_view(),name="double-converters/readings"),
	path('double-converters/historical-trendings',DoubleconverterTrendingsView.as_view(),name="double-converters/historical-trendings"),
	path('double-converters/operation-counts',OperationCountsView.as_view(),name="double-converters/operation-counts"),
	path('double-converters/operation-info',OperationInfoView.as_view(),name="double-converters/operation-info"),
	path('double-converters/operation-time',OperationTimeView.as_view(),name="double-converters/operation-time"),
	path('double-converters/power-status',PowerStatusView.as_view(),name="double-converters/power-status"),
	path('double-converters/cooling-fan',CoolingFanView.as_view(),name="double-converters/cooling-fan"),
	path('double-converters/cooling-fan-info',CoolingFanInfoView.as_view(),name="double-converters/cooling-fan-info"),
	path('double-converters/element-temperature',ElementTemperatureView.as_view(),name="double-converters/element-temperature"),
	path('double-converters/prediction-models',DoubleconverterPredictionsView.as_view(),name="double-converters/prediction-models"),

	path('rectifiers',RectifierView.as_view(),name="rectifiers"),
	path('rectifiers/readings',RectifierReadingsView.as_view(),name="rectifiers/readings"),
	path('rectifiers/historical-trendings',RectifierTrendingsView.as_view(),name="rectifiers/historical-trendings"),
	path('rectifiers/panel-temperatures',PanelTemperatureView.as_view(),name="rectifiers/panel-temperatures"),
	
	path('inverters',InverterView.as_view(),name="inverters"),
	path('inverters/panel-temperatures',InverterPanelTemperatureView.as_view(),name="inverters/panel-temperatures"),
	path('inverters/operation-counts',NumberOfOperationsView.as_view(),name="inverters/operation-counts"),
	path('inverters/power-status',MaximumPowerView.as_view(),name="inverters/power-status"),
	path('inverters/operation-info',InverterOperationInfoView.as_view(),name="inverters/operation-info"),
	path('inverters/readings',InverterReadingsView.as_view(),name="inverters/readings"),
	path('inverters/historical-trendings',InverterTrendingsView.as_view(),name="inverters/historical-trendings")

]

	
	

	


