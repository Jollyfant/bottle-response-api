import os
import numpy as np
from bottle import hook, route, run, request, HTTPError
from obspy import read_inventory

def getSamplingRate(stages):

  # Loop over all the stages backwards until sampling rate is found
  for stage in stages[::-1]:
    if stage.decimation_input_sample_rate is not None and stage.decimation_factor is not None:
      return stage.decimation_input_sample_rate / stage.decimation_factor

@hook('after_request')
def enableCORS():

    """
    Enable Cross Origin Policies
    """

    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

def mapUnit(query):

  def getUnit(unit):
  
    if unit == "displacement":
      return "DISP"
    elif unit == "velocity":
      return "VEL"
    elif unit == "acceleration":
      return "ACC"
    else:
      return None

  # Unit was not specified in the query: default
  if "unit" not in query:
    return "VEL"

  # Try mapping the unit
  unit = getUnit(query["unit"])

  # Invalid unit was specified
  if unit is None:
    raise ValueError("Invalid output unit requested %s. Expected displacement, velocity, or acceleration" % key)

  return unit


def validateQuery(query):

  # Supported and required by the API
  SUPPORTED = ["network", "station", "location", "channel", "unit"]
  REQUIRED = ["network", "station", "location", "channel"]

  for key in query:
    if key not in SUPPORTED:
      raise ValueError("Key %s is not supported." % key)

  for key in REQUIRED:
    if key not in query:
      raise ValueError("Key %s is required." % key)

@route("/")
def index():

  # Constants
  FDSN_STATION_URL = "http://www.orfeus-eu.org/fdsnws/station/1/query"
  F_MIN = 1E-2

  query = dict(request.query)

  # Validate sanity of query
  try:
    validateQuery(query)
  except ValueError as exception:
    return HTTPError(400, exception)

  # Check validity of unit parameter
  try:
    unit = mapUnit(query)
  except ValueError as exception:
    return HTTPError(400, exception)

  # Read the inventory to ObsPy
  inventory = read_inventory(FDSN_STATION_URL + "?" + request.query_string + "&level=response")

  # Only return the first channel
  # TODO add start & end time
  for network in inventory:
    for station in network:
      for channel in station:

        # Parameters for deconvolution
        samplingRate = getSamplingRate(channel.response.response_stages)
        nFFT = samplingRate / F_MIN
        nyquist = 0.5 * samplingRate
        tSamp = 1.0 / samplingRate

        response, freq = channel.response.get_evalresp_response(
          t_samp=tSamp,
          nfft=nFFT,
          output=unit
        )

        # Convert imag numbers to phase and amplitude
        amplitude = map(lambda x: np.abs(x), response)
        phase = map(lambda x: np.angle(x), response)

        return {
          "nyquist": nyquist,
          "samplingRate": samplingRate,
          "channel": ".".join([network.code, station.code, channel.location_code, channel.code]),
          "amplitude": amplitude[1:],
          "phase": phase[1:],
          "frequency": list(freq)[1:]
        }

run(
  host=(os.environ.get("SERVICE_HOST") or "0.0.0.0"),
  port=(os.environ.get("SERVICE_PORT") or 8080)
)
