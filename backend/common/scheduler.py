# -*- coding: utf-8 -*-
"""后台定时任务调度器"""

from __future__ import annotations

import os
import threading
from datetime import datetime

from backend.app.admin.model.scheduled_task import get_scheduled_task_model, get_scheduled_task_run_model
from backend.app.admin.service.scheduled_task import ScheduledTaskService


class ScheduledTaskRunner:
    def __init__(self, app, db, models, interval_seconds=20):
        self.app = app
        self.db = db
        self.models = models
        self.interval_seconds = max(5, int(interval_seconds or 20))
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._loop, name='scheduled-task-runner', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _loop(self):
        with self.app.app_context():
            task_model = get_scheduled_task_model(self.models)
            run_model = get_scheduled_task_run_model(self.models)
            service = ScheduledTaskService(self.db, task_model, run_model)

            while not self._stop_event.is_set():
                try:
                    self._execute_due_tasks(task_model, service)
                except Exception:
                    self.db.session.rollback()
                self._stop_event.wait(self.interval_seconds)

    def _execute_due_tasks(self, task_model, service):
        now = datetime.utcnow()
        due_tasks = task_model.query.filter(
            task_model.is_active.is_(True),
            task_model.next_run_at.isnot(None),
            task_model.next_run_at <= now,
        ).order_by(task_model.next_run_at.asc()).limit(20).all()

        for item in due_tasks:
            claimed = task_model.query.filter(
                task_model.id == item.id,
                task_model.is_active.is_(True),
                task_model.next_run_at == item.next_run_at,
            ).update({
                task_model.next_run_at: None,
                task_model.last_status: 'running',
            }, synchronize_session=False)
            self.db.session.commit()

            if not claimed:
                continue

            task = task_model.query.get(item.id)
            if not task:
                continue

            service.execute_task(task, trigger_type='scheduled')


def init_scheduled_task_runner(app, db, models):
    if app.extensions.get('scheduled_task_runner'):
        return

    enabled = str(app.config.get('ENABLE_TASK_SCHEDULER', 'true')).strip().lower() in {'1', 'true', 'yes', 'on'}
    if not enabled:
        return

    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    runner = ScheduledTaskRunner(
        app=app,
        db=db,
        models=models,
        interval_seconds=app.config.get('TASK_SCHEDULER_INTERVAL_SECONDS', 20),
    )
    runner.start()
    app.extensions['scheduled_task_runner'] = runner
