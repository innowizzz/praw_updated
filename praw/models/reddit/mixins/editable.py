"""Provide the EditableMixin class."""
import re
from json import dumps
from typing import TYPE_CHECKING, Dict, Optional, Union

from ....const import API_PATH

if TYPE_CHECKING:  # pragma: no cover
    import praw

INLINE_MEDIA_PATTERN = re.compile(
    r"\n\n!?(\[.*?])?\(?((https://((preview|i)\.redd\.it|reddit.com/link).*?)|(?!https)([a-zA-Z0-9]+( \".*?\")?))\)?"
)
MEDIA_TYPE_MAPPING = {
    "Image": "img",
    "RedditVideo": "video",
    "AnimatedImage": "gif",
}


class EditableMixin:
    """Interface for classes that can be edited and deleted."""

    def _replace_richtext_links(self, richtext_json: dict):
        if hasattr(self, "media_metadata"):
            parsed_media_types = {}
            for media_id, value in self.media_metadata.items():
                parsed_media_types[media_id] = MEDIA_TYPE_MAPPING[value["e"]]

            for index, element in enumerate(richtext_json["document"][:]):
                element_items = element.get("c")
                if isinstance(element_items, str):
                    assert element.get("e") in ["gif", "img", "video"], (
                        "Unexpected richtext JSON schema. Please file a bug report with"
                        " PRAW."
                    )  # make sure this is an inline element
                    continue  # pragma: no cover
                for item in element.get("c"):
                    if item.get("e") == "link":
                        ids = set(parsed_media_types)
                        # remove extra bits from the url
                        url = item["u"].split("https://")[1].split("?")[0]
                        # the id is in the url somewhere, so we split by / and .
                        matched_id = ids.intersection(re.split(r"[./]", url))
                        if matched_id:
                            matched_id = matched_id.pop()
                            correct_element = {
                                "e": parsed_media_types[matched_id],
                                "id": matched_id,
                            }
                            if item.get("t") != item.get(
                                "u"
                            ):  # add caption if it exists
                                correct_element["c"] = item["t"]
                            richtext_json["document"][index] = correct_element

    def delete(self):
        """Delete the object.

        Example usage:

        .. code-block:: python

            comment = reddit.comment("dkk4qjd")
            comment.delete()

            submission = reddit.submission("8dmv8z")
            submission.delete()

        """
        self._reddit.post(API_PATH["del"], data={"id": self.fullname})

    def edit(
        self,
        body: str,
        *,
        preserve_inline_media=False,
        inline_media: Optional[Dict[str, "praw.models.InlineMedia"]] = None
    ) -> Union["praw.models.Comment", "praw.models.Submission"]:
        """Replace the body of the object with ``body``.

        :param body: The Markdown formatted content for the updated object.
        :param preserve_inline_media: Attempt to preserve inline media in ``body``.

            .. danger::

                This is experimental. It is reliant on undocumented API endpoints and
                may result in existing inline media not displaying correctly and/or
                creating a malformed body. Use at your own risk.

        :param inline_media: A dictionary of inline media to be used in ``body``.

        :returns: The current instance after updating its attributes.

        Example usage:

        .. code-block:: python

            comment = reddit.comment("dkk4qjd")

            # construct the text of an edited comment
            # by appending to the old body:
            edited_body = comment.body + "Edit: thanks for the gold!"
            comment.edit(edited_body)

        """
        data = {
            "thing_id": self.fullname,
            "validate_on_submit": self._reddit.validate_on_submit,
        }
        is_richtext_json = False
        if INLINE_MEDIA_PATTERN.search(body):
            is_richtext_json = True
        if inline_media:
            body = body.format(
                **{
                    placeholder: self.subreddit._upload_inline_media(media)
                    for placeholder, media in inline_media.items()
                }
            )
            is_richtext_json = True
        if is_richtext_json:
            richtext_json = self.subreddit._convert_to_fancypants(body)
            if preserve_inline_media:
                self._replace_richtext_links(richtext_json)
            data["richtext_json"] = dumps(richtext_json)
        else:
            data["text"] = body
        updated = self._reddit.post(API_PATH["edit"], data=data)
        if not is_richtext_json:
            updated = updated[0]
            for attribute in [
                "_fetched",
                "_reddit",
                "_submission",
                "replies",
                "subreddit",
            ]:
                if attribute in updated.__dict__:
                    delattr(updated, attribute)
            self.__dict__.update(updated.__dict__)
        else:
            self.__dict__.update(updated)
        return self  # type: ignore
