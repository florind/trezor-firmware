# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import json

import click

from .. import cardano, messages, tools
from . import ChoiceType, with_client

PATH_HELP = "BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"

ADDRESS_TYPES = {
    "byron": messages.CardanoAddressType.BYRON,
    "base": messages.CardanoAddressType.BASE,
    "pointer": messages.CardanoAddressType.POINTER,
    "enterprise": messages.CardanoAddressType.ENTERPRISE,
    "reward": messages.CardanoAddressType.REWARD,
}


@click.group(name="cardano")
def cli():
    """Cardano commands."""


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.option(
    "-s",
    "--signing-mode",
    required=True,
    type=ChoiceType({m.name: m for m in messages.CardanoTxSigningMode}),
)
@click.option(
    "-p", "--protocol-magic", type=int, default=cardano.PROTOCOL_MAGICS["mainnet"]
)
@click.option("-N", "--network-id", type=int, default=cardano.NETWORK_IDS["mainnet"])
@click.option("-t", "--testnet", is_flag=True)
@with_client
def sign_tx(client, file, signing_mode, protocol_magic, network_id, testnet):
    """Sign Cardano transaction."""
    transaction = json.load(file)

    if testnet:
        protocol_magic = cardano.PROTOCOL_MAGICS["testnet"]
        network_id = cardano.NETWORK_IDS["testnet"]

    inputs = [cardano.parse_input(input) for input in transaction["inputs"]]
    outputs = [cardano.parse_output(output) for output in transaction["outputs"]]
    fee = transaction["fee"]
    ttl = transaction.get("ttl")
    validity_interval_start = transaction.get("validity_interval_start")
    certificates = [
        cardano.parse_certificate(certificate)
        for certificate in transaction.get("certificates", ())
    ]
    withdrawals = [
        cardano.parse_withdrawal(withdrawal)
        for withdrawal in transaction.get("withdrawals", ())
    ]
    auxiliary_data = cardano.parse_auxiliary_data(transaction.get("auxiliary_data"))

    sign_tx_response = cardano.sign_tx(
        client,
        signing_mode,
        inputs,
        outputs,
        fee,
        ttl,
        validity_interval_start,
        certificates,
        withdrawals,
        protocol_magic,
        network_id,
        auxiliary_data,
    )

    sign_tx_response["tx_hash"] = sign_tx_response["tx_hash"].hex()
    sign_tx_response["witnesses"] = [
        {
            "type": witness["type"],
            "pub_key": witness["pub_key"].hex(),
            "signature": witness["signature"].hex(),
            "chain_code": witness["chain_code"].hex()
            if witness["chain_code"] is not None
            else None,
        }
        for witness in sign_tx_response["witnesses"]
    ]
    auxiliary_data_supplement = sign_tx_response.get("auxiliary_data_supplement")
    if auxiliary_data_supplement:
        auxiliary_data_supplement["auxiliary_data_hash"] = auxiliary_data_supplement[
            "auxiliary_data_hash"
        ].hex()
        catalyst_signature = auxiliary_data_supplement.get("catalyst_signature")
        if catalyst_signature:
            auxiliary_data_supplement["catalyst_signature"] = catalyst_signature.hex()
        sign_tx_response["auxiliary_data_supplement"] = auxiliary_data_supplement
    return sign_tx_response


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-t", "--address-type", type=ChoiceType(ADDRESS_TYPES), default="base")
@click.option("-s", "--staking-address", type=str, default=None)
@click.option("-h", "--staking-key-hash", type=str, default=None)
@click.option("-b", "--block_index", type=int, default=None)
@click.option("-x", "--tx_index", type=int, default=None)
@click.option("-c", "--certificate_index", type=int, default=None)
@click.option(
    "-p", "--protocol-magic", type=int, default=cardano.PROTOCOL_MAGICS["mainnet"]
)
@click.option("-N", "--network-id", type=int, default=cardano.NETWORK_IDS["mainnet"])
@click.option("-e", "--testnet", is_flag=True)
@with_client
def get_address(
    client,
    address,
    address_type,
    staking_address,
    staking_key_hash,
    block_index,
    tx_index,
    certificate_index,
    protocol_magic,
    network_id,
    show_display,
    testnet,
):
    """
    Get Cardano address.

    All address types require the address, address_type, protocol_magic and
    network_id parameters.

    When deriving a base address you can choose to include staking info as
    staking_address or staking_key_hash - one has to be chosen.

    When deriving a pointer address you need to specify the block_index,
    tx_index and certificate_index parameters.

    Byron, enterprise and reward addresses only require the general parameters.
    """
    if testnet:
        protocol_magic = cardano.PROTOCOL_MAGICS["testnet"]
        network_id = cardano.NETWORK_IDS["testnet"]

    staking_key_hash_bytes = None
    if staking_key_hash:
        staking_key_hash_bytes = bytes.fromhex(staking_key_hash)

    address_parameters = cardano.create_address_parameters(
        address_type,
        tools.parse_path(address),
        tools.parse_path(staking_address),
        staking_key_hash_bytes,
        block_index,
        tx_index,
        certificate_index,
    )

    return cardano.get_address(
        client, address_parameters, protocol_magic, network_id, show_display
    )


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@with_client
def get_public_key(client, address):
    """Get Cardano public key."""
    address_n = tools.parse_path(address)
    return cardano.get_public_key(client, address_n)
