#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2020 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

from datetime import datetime

import pandas as pd

from examples.strategies.ema_cross_simple import EMACross
from nautilus_trader.backtest.config import BacktestConfig
from nautilus_trader.backtest.data import BacktestDataContainer
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.loaders import InstrumentLoader
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.common.logging import LogLevel
from nautilus_trader.model.bar import BarSpecification
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.enums import OMSType
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import Venue
from tests.test_kit.data import TestDataProvider

if __name__ == "__main__":
    symbol = Symbol('USD/JPY', Venue('FXCM'))
    USDJPY = InstrumentLoader.default_fx_ccy(symbol)

    data = BacktestDataContainer()
    data.add_instrument(USDJPY)
    data.add_bars(
        USDJPY.symbol,
        BarAggregation.MINUTE,
        PriceType.BID,
        TestDataProvider.usdjpy_1min_bid(),  # Stub data from the test kit
    )
    data.add_bars(
        USDJPY.symbol,
        BarAggregation.MINUTE,
        PriceType.ASK,
        TestDataProvider.usdjpy_1min_ask(),  # Stub data from the test kit
    )

    strategies = [EMACross(
        symbol=USDJPY.symbol,
        bar_spec=BarSpecification(
            5,
            BarAggregation.MINUTE,
            PriceType.BID,
        ),
        fast_ema=10,
        slow_ema=20,
    )]

    config = BacktestConfig(
        exec_db_type="in-memory",
        exec_db_flush=False,
        frozen_account=False,
        starting_capital=1000000,
        account_currency=USD,
        short_term_interest_csv_path="default",
        bypass_logging=False,
        level_console=LogLevel.INFO,
        level_file=LogLevel.DEBUG,
        level_store=LogLevel.WARNING,
        log_thread=False,
        log_to_file=False,
    )

    fill_model = FillModel(
        prob_fill_at_limit=0.2,
        prob_fill_at_stop=0.95,
        prob_slippage=0.5,
        random_seed=42,
    )

    engine = BacktestEngine(
        data=data,
        strategies=strategies,
        venue=Venue("FXCM"),
        oms_type=OMSType.HEDGING,
        generate_position_ids=False,
        config=config,
        fill_model=fill_model,
    )

    input("Press Enter to continue...")  # noqa (always Python 3)

    start = datetime(2013, 2, 1, 0, 0, 0, 0)
    stop = datetime(2013, 3, 1, 0, 0, 0, 0)

    engine.run(start, stop)

    with pd.option_context(
            "display.max_rows",
            100,
            "display.max_columns",
            None,
            "display.width", 300):
        print(engine.trader.generate_account_report(AccountId.from_string("FXCM-000-SIMULATED")))
        print(engine.trader.generate_order_fills_report())
        print(engine.trader.generate_positions_report())

    engine.dispose()