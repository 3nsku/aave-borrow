from brownie import (
    network,
    config,
    interface,
)
from scripts.helpful_scripts import get_account
from scripts.get_weth import get_weth
from web3 import Web3


AMOUNT = Web3.toWei(0.1, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in ["mainnet-fork-dev"]:
        get_weth()
    lending_pool = get_lending_pool()

    approve_erc20(AMOUNT, lending_pool.address, erc20_address, account)
    print("Depositing...")
    tx = lending_pool.deposit(
        erc20_address, AMOUNT, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Deposited!")

    borrowable_eth, total_debt_eth = get_borrowable_data(lending_pool, account)

    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )

    amount_dai_to_borrow = (0.95 * borrowable_eth) / dai_eth_price
    print(f"We are going to Borrow {amount_dai_to_borrow} DAI")
    dai_token = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_token,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print("We have borrowed some DAI")
    get_borrowable_data(lending_pool, account)
    repay_all(2 ** 256, lending_pool, account)
    get_borrowable_data(lending_pool, account)


def repay_all(amount, lending_pool, account):
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool.address,
        config["networks"][network.show_active()]["dai_token"],
        account.address,
    )

    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["dai_token"],
        amount,
        1,
        account.address,
        {"from": account},
    )
    repay_tx.wait(1)
    print("Repayed!")


def get_asset_price(price_feed_address):
    price_feed_contract = interface.AggregatorV3Interface(price_feed_address)
    price = price_feed_contract.latestRoundData()[1]  # return price in 18 decimals
    converted_latest_price = Web3.fromWei(price, "ether")
    print(f"The DAI / ETH conversion: {converted_latest_price}")
    return float(converted_latest_price)


def approve_erc20(amount, spender, erc20_address, account):
    print("Approving ERC20 token")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Sender Approved")
    return tx


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_ETH,
        total_debt_ETH,
        available_borrows_ETH,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)

    available_borrows_ETH = Web3.fromWei(available_borrows_ETH, "ether")
    total_collateral_ETH = Web3.fromWei(total_collateral_ETH, "ether")
    total_debt_ETH = Web3.fromWei(total_debt_ETH, "ether")

    print(f"You have {total_collateral_ETH} worth of ETH deposited")
    print(f"You have {total_debt_ETH} worth of ETH borrowed")
    print(f"You have {available_borrows_ETH} worth of ETH Availbale to Borrow")

    return (float(available_borrows_ETH), float(total_debt_ETH))


def get_lending_pool():
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool
