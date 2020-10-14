from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from flask_ngrok import run_with_ngrok
from torch import nn

from active_labeling.backend.database.storage import Storage, StorageHandler
from active_labeling.backend.resources.annotate import Annotate
from active_labeling.backend.resources.annotations import Annotations
from active_labeling.backend.resources.config import Config
from active_labeling.backend.resources.metrics import Metrics
from active_labeling.backend.resources.query import Query
from active_labeling.backend.resources.teach import Teach
from active_labeling.backend.utils import load_json_file
from active_labeling.config import ActiveLearningConfig
from active_labeling.loading.base_loader import BaseDataLoader
from active_labeling.loading.image_loader import ImageLoader


class ActiveLearning:
    def __init__(self,
                 learner: nn.Module,
                 config: ActiveLearningConfig,
                 data_loader: BaseDataLoader = ImageLoader()):
        self._app = Flask(__name__)
        self._api = Api(self._app)
        CORS(self._app)

        storage_handler = self._load_data(config, data_loader)
        self._init_resources(storage_handler, learner)

    def _load_data(self,
                   config: ActiveLearningConfig,
                   data_loader: BaseDataLoader) -> StorageHandler:
        unlabeled_data = data_loader.load(config.unlabeled_data_path)
        data_labels = load_json_file(config.labels_file)['annotations']

        validation_data = data_loader.load(config.validation_data_path)
        validation_labels = load_json_file(config.validation_labels_path)['annotations']

        storage = Storage(unlabeled_data, config, data_labels, validation_data, validation_labels)
        return StorageHandler(storage)

    def _init_resources(self,
                        storage_handler: StorageHandler,
                        learner: nn.Module) -> None:
        resources = (
            Query.instantiate(storage_handler, learner),
            Teach.instantiate(storage_handler, learner),
            Annotate.instantiate(storage_handler),
            Config.instantiate(storage_handler),
            Metrics.instantiate(storage_handler),
            Annotations.instantiate(storage_handler),
        )

        for resource in resources:
            self._api.add_resource(resource, resource.endpoint)

    def run(self, ngrok=False) -> None:
        if ngrok:
            run_with_ngrok(self._app)
        self._app.run()
