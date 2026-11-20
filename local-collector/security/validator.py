from typing import Any, Dict, List, Optional, Tuple
from pydantic import ValidationError
from models.payload import OutgoingPayload
from models.metric import SystemMetrics


class PayloadValidator:
    """Validator ensuring payload strictly conforms to schemas with extra='forbid'."""

    @staticmethod
    def validate_outgoing_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[OutgoingPayload], List[str]]:
        try:
            model = OutgoingPayload(**data)
            return True, model, []
        except ValidationError as e:
            errors = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [str(e)]

    @staticmethod
    def validate_system_metrics(data: Dict[str, Any]) -> Tuple[bool, Optional[SystemMetrics], List[str]]:
        try:
            model = SystemMetrics(**data)
            return True, model, []
        except ValidationError as e:
            errors = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]
            return False, None, errors
        except Exception as e:
            return False, None, [str(e)]
