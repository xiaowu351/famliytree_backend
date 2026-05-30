#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from wxcloudrun.app import app

print("已注册的所有路由:")
print("=" * 60)
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"{rule.rule:40} {methods}")
print("=" * 60)
print(f"总共 {len([r for r in app.url_map.iter_rules() if r.endpoint != 'static'])} 个路由")
