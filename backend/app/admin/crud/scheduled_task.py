# -*- coding: utf-8 -*-
"""定时任务 CRUD 层"""


class ScheduledTaskCRUD:
    def __init__(self, db, task_model, run_model):
        self.db = db
        self.ScheduledTask = task_model
        self.ScheduledTaskRun = run_model

    def task_query(self):
        return self.ScheduledTask.query

    def run_query(self):
        return self.ScheduledTaskRun.query

    def get_task_or_404(self, task_id):
        return self.ScheduledTask.query.get_or_404(task_id)

    def get_task_by_code(self, task_code):
        return self.ScheduledTask.query.filter_by(task_code=task_code).first()

    def list_tasks_by_ids(self, ids):
        return self.ScheduledTask.query.filter(self.ScheduledTask.id.in_(ids))

    def add(self, item):
        self.db.session.add(item)

    def delete(self, item):
        self.db.session.delete(item)

    def commit(self):
        self.db.session.commit()

    def rollback(self):
        self.db.session.rollback()
