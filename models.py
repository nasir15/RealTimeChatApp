from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class ChatGroup(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_groups', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_chat_groups',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:130] or 'chat-group'
            slug = base_slug
            index = 1
            while ChatGroup.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base_slug}-{index}'
                index += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        ChatGroup,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True,
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('timestamp', 'id')
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(receiver__isnull=False) & Q(group__isnull=True))
                    | (Q(receiver__isnull=True) & Q(group__isnull=False))
                ),
                name='message_has_private_or_group_target',
            ),
        ]

    def clean(self):
        has_receiver = bool(self.receiver_id)
        has_group = bool(self.group_id)
        if has_receiver == has_group:
            raise ValidationError('Message must belong to exactly one conversation target.')

    @property
    def conversation_label(self):
        if self.group_id:
            return self.group.name
        return f'{self.sender.username} -> {self.receiver.username}'

    def __str__(self):
        return f'{self.sender} @ {self.timestamp:%Y-%m-%d %H:%M}'
