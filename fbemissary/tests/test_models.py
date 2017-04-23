# Licensed under the Apache License:
#     http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/cdunklau/fbemissary/blob/master/NOTICE.txt
import json

import pytest
import attr

from fbemissary import models


def make_test_params():
    params = []
    params.append((
        '''{
          "sender":{"id":"USER_ID"},
          "recipient":{"id":"PAGE_ID"},
          "timestamp":1458692752478,
          "message":{
            "mid":"mid.1457764197618:41d102a3e1ae206a38",
            "text":"hello, world!",
            "quick_reply": {
              "payload": "DEVELOPER_DEFINED_PAYLOAD"
            }
          }
        }''',
        models.ReceivedMessage(
            sender_id='USER_ID',
            recipient_id='PAGE_ID',
            timestamp=1458692752478,
            id='mid.1457764197618:41d102a3e1ae206a38',
            text='hello, world!',
            attachments=[],
            quick_reply='DEVELOPER_DEFINED_PAYLOAD',
        )
    ))
    params.append((
        '''{
          "sender":{"id":"USER_ID"},
          "recipient":{"id":"PAGE_ID"},
          "timestamp":1458692752478,
          "message":{
            "mid":"mid.1458696618141:b4ef9d19ec21086067",
            "attachments":[
              {
                "type":"image",
                "payload":{"url":"IMAGE_URL"}
              }
            ]
          }
        }''',
        models.ReceivedMessage(
            sender_id='USER_ID',
            recipient_id='PAGE_ID',
            timestamp=1458692752478,
            id='mid.1458696618141:b4ef9d19ec21086067',
            text=None,
            attachments=[
                models.MediaAttachment(
                    type=models.AttachmentType.image,
                    url='IMAGE_URL',
                )
            ],
            quick_reply=None,
        )
    ))
    params.append((
        '''{
          "sender":{"id":"USER_ID"},
          "recipient":{"id":"PAGE_ID"},
          "timestamp":1458692752478,
          "message":{
            "mid":"mid.1458696618141:b4ef9d19ec21086067",
            "attachments":[
              {
                "type":"location",
                "payload":{
                  "coordinates":{"lat":37.48336,"long":-122.15008}
                }
              }
            ]
          }
        }''',
        models.ReceivedMessage(
            sender_id='USER_ID',
            recipient_id='PAGE_ID',
            timestamp=1458692752478,
            id='mid.1458696618141:b4ef9d19ec21086067',
            text=None,
            attachments=[
                models.LocationAttachment(
                    type=models.AttachmentType.location,
                    latitude=37.48336,
                    longitude=-122.15008,
                )
            ],
            quick_reply=None,
        )
    ))
    return 'jsondoc,value', params


@pytest.mark.parametrize(*make_test_params())
def test_model_from_entry_structure(jsondoc, value):
    structure = json.loads(jsondoc)
    result = models.model_from_entry_structure(structure)
    assert attr.asdict(result) == attr.asdict(value)
