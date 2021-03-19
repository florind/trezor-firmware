import storage.device
from trezor import ui, wire
from trezor.messages import ButtonRequestType
from trezor.messages.GetNextU2FCounter import GetNextU2FCounter
from trezor.messages.NextU2FCounter import NextU2FCounter
from trezor.ui.layouts import confirm_action


async def get_next_u2f_counter(
    ctx: wire.Context, msg: GetNextU2FCounter
) -> NextU2FCounter:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    await confirm_action(
        ctx,
        "get_u2f_counter",
        title="Get next U2F counter",
        description="Do you really want to\n{}\nthe U2F counter?",
        description_param="increase and retrieve",
        icon=ui.ICON_CONFIG,
        br_code=ButtonRequestType.ProtectCall,
    )

    return NextU2FCounter(u2f_counter=storage.device.next_u2f_counter())
