from fastapi import HTTPException


ALLOWED_TRANSITION ={
    "open":{"in_progress"},
    "in_progress":{"resolved","open"},
    "resolved":{"closed","in_progress"},
    "closed":set()

}



def validate_transition(
    current_status:str,
    new_status:str
):
    allowed = ALLOWED_TRANSITION.get(current_status,set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition "
                f"{current_status}->{new_status}"

            )
        )