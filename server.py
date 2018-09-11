"""

  EIDA Instrument Response API
  Returns frequency response data pulled from FDSNWS.

  Powered by Bottle & Obspy

  Author: Mathijs Koymans, 2018
  Copyright: ORFEUS Data Center, 2018
  All Rights Reserved

"""

import os
import json
import numpy as np
from bottle import hook, route, run, request, response, HTTPError, HTTPResponse
from obspy import read_inventory

with open("config.json") as configuration:
  CONFIG = json.load(configuration)

def getSamplingRate(stages):

  # Loop over all the stages backwards until sampling rate is found
  for stage in stages[::-1]:
    if stage.decimation_input_sample_rate is not None and stage.decimation_factor is not None:
      return stage.decimation_input_sample_rate / stage.decimation_factor

@hook("after_request")
def enableCORS():

    """
    Enable Cross Origin Policies
    """

    # Set the headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "PUT, GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token"

def mapUnit(query):

  def getUnit(unit):
 
    if unit == "displacement":
      return "DISP"
    elif unit == "velocity":
      return "VEL"
    elif unit == "acceleration":
      return "ACC"
    else:
      raise ValueError("Invalid output unit requested %s. Expected displacement, velocity, or acceleration" % key)

  # Unit was not specified in the query: default
  if "unit" not in query:
    return "VEL"

  return getUnit(query["unit"])


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
  F_MIN = 1E-2

  # Conver to a simple dict
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
  # If this fails just send 204
  try:
    inventory = read_inventory(CONFIG["FDSN_STATION_URL"] + "?" + request.query_string + "&level=response")
  except Exception as exception:
    return HTTPResponse(status=204)

  # Only return the first channel
  for network in inventory:
    for station in network:
      for channel in station:

        channelIdentifier = ".".join([
          network.code,
          station.code,
          channel.location_code,
          channel.code
        ])

        # Parameters for deconvolution
        samplingRate = getSamplingRate(channel.response.response_stages)

        nFFT = samplingRate / F_MIN
        nyquist = 0.5 * samplingRate
        tSamp = 1.0 / samplingRate

        # Pass to evalresp routine
        polar, freq = channel.response.get_evalresp_response(
          t_samp=tSamp,
          nfft=nFFT,
          output=unit
        )

        # Convert imag numbers to phase and amplitude
        amplitude = np.abs(polar)
        phase = np.angle(polar)

        # Skip first value (freq. 0)
        return {
          "nyquist": nyquist,
          "samplingRate": samplingRate,
          "channel": channelIdentifier,
          "amplitude": list(amplitude[1:]),
          "phase": list(phase[1:]),
          "frequency": list(freq)[1:]
        }

  # Return empty
  return HTTPResponse(status=204)

run(
  host=(os.environ.get("SERVICE_HOST") or "0.0.0.0"),
  port=(os.environ.get("SERVICE_PORT") or 8080)
)
