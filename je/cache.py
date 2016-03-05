########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############

import json

from je.configuration import configuration


class Cache(object):

    @property
    def cache_dir(self):
        return configuration.conf_dir / 'cache'

    @property
    def logs_dir(self):
        return self.cache_dir / 'logs'

    def save(self, key, value):
        key_path = self._key_path(key)
        key_path.write_text(json.dumps(value,
                                       indent=2,
                                       sort_keys=True))

    def save_log(self, key, value):
        log_path = self._log_path(key)
        log_path.write_text(value, encoding='utf8')

    def load(self, key):
        key_path = self._key_path(key)
        if not key_path.exists():
            return None
        return json.loads(key_path.text())

    def load_log(self, key):
        log_path = self._log_path(key)
        if not log_path.exists():
            return ''
        return log_path.text(encoding='utf8')

    def clear(self):
        self.cache_dir.rmtree_p()
        self.cache_dir.mkdir()
        self.logs_dir.mkdir()

    def _log_path(self, key):
        return self.logs_dir / '{}.log'.format(key)

    def _key_path(self, key):
        return self.cache_dir / '{}.json'.format(key)
cache = Cache()
