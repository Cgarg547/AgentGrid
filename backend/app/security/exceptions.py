class ApprovalRequired(Exception):
    def __init__(
        self,
        request_id: str,
    ):
        self.request_id = request_id

        super().__init__(
            f"Approval is required for request "
            f"'{request_id}'."
        )