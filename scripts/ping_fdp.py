import json
import urllib.request

body = json.dumps({"clientUrl": "https://<#URLofYourServer#>/api/fdp"}).encode("utf-8")
req = urllib.request.Request("https://home.fairdatapoint.org")
req.add_header("Content-Type", "application/json; charset=utf-8")
response = urllib.request.urlopen(req, body)
