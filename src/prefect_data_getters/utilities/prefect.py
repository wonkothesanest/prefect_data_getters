from prefect.client.orchestration import get_client
from prefect.client.schemas.sorting import FlowRunSort
from prefect.client.schemas.filters import FlowFilter, FlowFilterName, FlowRunFilter, FlowRunFilterState, FlowRunFilterStateName
from prefect.states import Completed





def get_last_successful_flow_run_timestamp(flow_name: str):
    """
    Retrieves the timestamp of the last successful run of the given flow.
    """
    client = get_client(sync_client=True)
    flow_runs = client.read_flow_runs(
        limit=1,
        sort=FlowRunSort.START_TIME_DESC,
        flow_filter=FlowFilter(name=FlowFilterName(any_=[flow_name])),
        flow_run_filter=FlowRunFilter(state=dict(name=dict(any_=["Completed"]))
    ))

    if flow_runs:
        return flow_runs[0].start_time.timestamp()
    else:
        return None