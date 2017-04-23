# Licensed under the Apache License:
#     http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/cdunklau/fbemissary/blob/master/NOTICE.txt
import enum

import attr


def model_from_entry_structure(entry):
    if 'message' in entry:
        return ReceivedMessage.from_message_structure(entry)
    else:
        raise ValueError(
            'Unsupported entry type in entry {0!r}'.format(entry)
        )


@attr.s
class ReceivedMessage:
    sender_id = attr.ib()
    recipient_id = attr.ib()
    timestamp = attr.ib()
    id = attr.ib()
    text = attr.ib()  # Not necessarily present if message has attachment
    attachments = attr.ib()  # Not necessarily present if message has text
    quick_reply = attr.ib()  # Optional custom data from sending app (the bot)

    @classmethod
    def from_message_structure(cls, structure):
        mstruct = structure['message']
        quick_reply = mstruct.get('quick_reply', {'payload': None})['payload']
        return cls(
            sender_id=structure['sender']['id'],
            recipient_id=structure['recipient']['id'],
            timestamp=structure['timestamp'],
            id=mstruct['mid'],
            text=mstruct.get('text'),
            attachments=[
                _attachment_from_structure(s)
                for s in mstruct.get('attachments', [])
            ],
            quick_reply=quick_reply,
        )


class AttachmentType(enum.Enum):
    audio = 'audio'
    file = 'file'
    image = 'image'
    video = 'video'
    location = 'location'


def _attachment_from_structure(structure):
    if structure['type'] == 'location':
        return LocationAttachment.from_structure(structure)
    else:
        return MediaAttachment.from_structure(structure)

@attr.s
class MediaAttachment:
    type = attr.ib()
    url = attr.ib()

    @classmethod
    def from_structure(cls, structure):
        typevalue = structure['type']
        assert typevalue != 'location', 'Need to use LocationAttachment'
        try:
            type = AttachmentType[typevalue]
        except KeyError:
            raise ValueError(
                "{0!r} is not a supported attachment type".format(typevalue))
        url = structure['payload']['url']
        return cls(type, url)


@attr.s
class LocationAttachment:
    type = attr.ib()
    latitude = attr.ib()
    longitude = attr.ib()

    @classmethod
    def from_structure(cls, structure):
        if structure['type'] != 'location':
            fmt = "Expected 'location' for type key but got {0!r}"
            raise ValueError(fmt.format(structure['type']))
        payload = structure['payload']
        return cls(
            AttachmentType.location,
            payload['coordinates']['lat'],
            payload['coordinates']['long'],
        )
