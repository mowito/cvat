# Copyright (C) 2021 Intel Corporation
#
# SPDX-License-Identifier: MIT

from typing import Callable

from django.db import transaction

from cvat.apps.engine import models
from cvat.apps.dataset_manager.task import TaskAnnotation

from .annotation import AnnotationIR
from .bindings import ProjectData, load_dataset_data
from .formats.registry import make_exporter, make_importer
from .util import bulk_create

def export_project(project_id, dst_file, format_name,
        server_url=None, save_images=False):
    # For big tasks dump function may run for a long time and
    # we dont need to acquire lock after the task has been initialized from DB.
    # But there is the bug with corrupted dump file in case 2 or
    # more dump request received at the same time:
    # https://github.com/opencv/cvat/issues/217
    with transaction.atomic():
        project = ProjectAnnotationAndData(project_id)
        project.init_from_db()

    exporter = make_exporter(format_name)
    with open(dst_file, 'wb') as f:
        project.export(f, exporter, host=server_url, save_images=save_images)

class ProjectAnnotationAndData:
    def __init__(self, pk: int):
        self.db_project = models.Project.objects.get(id=pk)
        self.db_tasks = models.Task.objects.filter(project__id=pk).order_by('id')

        self.task_annotations: dict[int, TaskAnnotation] = dict()
        self.annotation_irs: dict[int, AnnotationIR] = dict()

        self.tasks_to_add: list[models.Task] = []

    def reset(self):
        for annotation_ir in self.annotation_irs.values():
            annotation_ir.reset()

    def put(self, data):
        raise NotImplementedError()

    def create(self, data):
        raise NotImplementedError()

    def update(self, data):
        raise NotImplementedError()

    def delete(self, data=None):
        raise NotImplementedError()

    def add_task(self, task: models.Task):
        self.tasks_to_add.append(task)

    def init_from_db(self):
        self.reset()

        for task in self.db_tasks:
            annotation = TaskAnnotation(pk=task.id)
            annotation.init_from_db()
            self.task_annotations[task.id] = annotation
            self.annotation_irs[task.id] = annotation.ir_data

    def export(self, dst_file: str, exporter: Callable, host: str='', **options):
        project_data = ProjectData(
            annotation_irs=self.annotation_irs,
            db_project=self.db_project,
            host=host
        )
        exporter(dst_file, project_data, **options)

    def load_dataset_data(self, *args, **kwargs):
        load_dataset_data(self, *args, **kwargs)


    def import_dataset(self, dataset_file, importer):
        project_data = ProjectData(
            annotation_irs=self.annotation_irs,
            db_project=self.db_project,
        )

        importer(dataset_file, project_data, self.load_dataset_data)

        # TODO: check if filter is needed here
        bulk_create(models.Task, self.tasks_to_add, {})
        self.tasks_to_add.clear()

    @property
    def data(self) -> dict:
        raise NotImplementedError()

@transaction.atomic
def import_dataset_as_project(project_id, dataset_file, format_name):
    project = ProjectAnnotationAndData(project_id)
    project.init_from_db()

    importer = make_importer(format_name)
    with open(dataset_file, 'rb') as f:
        project.import_dataset(f, importer)