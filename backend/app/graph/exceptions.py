class GraphNodeExecutionError(RuntimeError):
    def __init__(
        self,
        node_name: str,
        original_exception: Exception,
    ):
        self.node_name = node_name
        self.original_exception = original_exception

        super().__init__(str(original_exception))