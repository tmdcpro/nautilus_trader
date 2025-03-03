// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

use nautilus_model::data::Bar;
use pyo3::prelude::*;

use crate::{
    average::MovingAverageType, indicator::Indicator, momentum::kvo::KlingerVolumeOscillator,
};

#[pymethods]
impl KlingerVolumeOscillator {
    #[new]
    #[pyo3(signature = (fast_period, slow_period, signal_period, ma_type=None))]
    #[must_use]
    pub fn py_new(
        fast_period: usize,
        slow_period: usize,
        signal_period: usize,
        ma_type: Option<MovingAverageType>,
    ) -> Self {
        Self::new(fast_period, slow_period, signal_period, ma_type)
    }

    fn __repr__(&self) -> String {
        format!(
            "KlingerVolumeOscillator({},{},{},{})",
            self.fast_period, self.slow_period, self.signal_period, self.ma_type
        )
    }

    #[getter]
    #[pyo3(name = "name")]
    fn py_name(&self) -> String {
        self.name()
    }

    #[getter]
    #[pyo3(name = "fast_period")]
    const fn py_fast_period(&self) -> usize {
        self.fast_period
    }

    #[getter]
    #[pyo3(name = "slow_period")]
    const fn py_slow_period(&self) -> usize {
        self.slow_period
    }

    #[getter]
    #[pyo3(name = "signal_period")]
    const fn py_signal_period(&self) -> usize {
        self.signal_period
    }

    #[getter]
    #[pyo3(name = "has_inputs")]
    fn py_has_inputs(&self) -> bool {
        self.has_inputs()
    }

    #[getter]
    #[pyo3(name = "value")]
    const fn py_value(&self) -> f64 {
        self.value
    }

    #[getter]
    #[pyo3(name = "initialized")]
    const fn py_initialized(&self) -> bool {
        self.initialized
    }

    #[pyo3(name = "update_raw")]
    fn py_update_raw(&mut self, high: f64, low: f64, close: f64, volume: f64) {
        self.update_raw(high, low, close, volume);
    }

    #[pyo3(name = "handle_bar")]
    fn py_handle_bar(&mut self, bar: &Bar) {
        self.handle_bar(bar);
    }

    #[pyo3(name = "reset")]
    fn py_reset(&mut self) {
        self.reset();
    }
}
