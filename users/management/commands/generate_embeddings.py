# management/commands/generate_embeddings.py

from django.core.management.base import BaseCommand
from users.models import Video
from sentence_transformers import SentenceTransformer
import numpy as np

class Command(BaseCommand):
    help = 'Generate embeddings for videos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings for all videos, even if they already have one.'
        )

    def handle(self, *args, **options):
        model = SentenceTransformer('all-MiniLM-L6-v2')
        force = options['force']

        if force:
            videos = Video.objects.all()
        else:
            videos = Video.objects.filter(embedding__isnull=True)

        count = 0
        for video in videos:
            text = f"{video.title} {video.description}"
            embedding = model.encode(text)
            video.embedding = np.array(embedding, dtype=np.float32).tobytes()
            video.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Generated embeddings for {count} videos.'))

