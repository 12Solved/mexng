from .attachment_pattern_map_step import AttachmentPatternMapStep
from .attachment_pattern_step import AttachmentPatternStep
from .date_step import DateStep
from .extract_archive_step import ExtractArchiveStep
from .extract_attachment_step import ExtractAttachmentsStep
from .extract_extension_step import ExtractExtensionStep
from .foreach_step import ForEachStep
from .hello_step import HelloStep
from .match_message_id_step import MatchMessageIdStep
from .match_recipient_address_step import MatchRecipientAddressStep
from .match_sender_address_step import MatchSenderAddressStep
from .match_subject_step import MatchSubjectStep
from .save_attachment_step import SaveAttachmentStep
from .set_variable_step import SetVariableStep
from .timeout_step import TimeoutStep

STEP_REGISTRY = {
    "hello_step": HelloStep,
    "match_sender_address_step": MatchSenderAddressStep,
    "match_recipient_address_step": MatchRecipientAddressStep,
    "match_subject_step": MatchSubjectStep,
    "match_message_id_step": MatchMessageIdStep,
    "attachment_pattern_step": AttachmentPatternStep,
    "attachment_pattern_map_step": AttachmentPatternMapStep,
    "save_attachment_step": SaveAttachmentStep,
    "extract_attachment_step": ExtractAttachmentsStep,
    "extract_archive_step": ExtractArchiveStep,
    "foreach": ForEachStep,
    "extract_extension_step": ExtractExtensionStep,
    "timeout": TimeoutStep,
    "date_step": DateStep,
    "set_variable_step": SetVariableStep,
}
