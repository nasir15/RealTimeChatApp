from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import ChatGroupForm, LoginForm, SignUpForm
from .models import ChatGroup, Message

User = get_user_model()


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('realtime_chat:dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        raw_password = form.cleaned_data['password1']
        authenticated_user = authenticate(request, username=user.username, password=raw_password)
        if authenticated_user is not None:
            login(request, authenticated_user)
        return redirect('realtime_chat:dashboard')
    return render(request, 'realtime_chat/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('realtime_chat:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('realtime_chat:dashboard')
    return render(request, 'realtime_chat/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('realtime_chat:login')


@login_required
def dashboard(request):
    users = User.objects.exclude(pk=request.user.pk).order_by('username')
    groups = ChatGroup.objects.prefetch_related('members').order_by('name')
    group_form = ChatGroupForm()

    active_user = None
    active_group = None
    private_messages = Message.objects.none()
    group_messages = Message.objects.none()

    selected_username = request.GET.get('user')
    selected_group_slug = request.GET.get('group')

    if selected_username:
        active_user = get_object_or_404(User, username=selected_username)
        private_messages = Message.objects.filter(
            Q(sender=request.user, receiver=active_user)
            | Q(sender=active_user, receiver=request.user)
        ).select_related('sender', 'receiver')
    elif selected_group_slug:
        active_group = get_object_or_404(ChatGroup.objects.prefetch_related('members'), slug=selected_group_slug)
        if not active_group.members.filter(pk=request.user.pk).exists():
            messages.warning(request, 'Join the group to participate in the room.')
        group_messages = active_group.messages.select_related('sender', 'group')

    context = {
        'users': users,
        'groups': groups,
        'group_form': group_form,
        'active_user': active_user,
        'active_group': active_group,
        'is_active_group_member': bool(
            active_group and active_group.members.filter(pk=request.user.pk).exists()
        ),
        'private_messages': private_messages,
        'group_messages': group_messages,
    }
    return render(request, 'realtime_chat/dashboard.html', context)


@login_required
@require_POST
def create_group(request):
    dashboard_url = reverse('realtime_chat:dashboard')
    form = ChatGroupForm(request.POST)
    if form.is_valid():
        group = form.save(creator=request.user)
        messages.success(request, f'Group "{group.name}" created.')
        return redirect(f'{dashboard_url}?group={group.slug}')
    messages.error(request, 'Please correct the group details and try again.')
    return render(request, 'realtime_chat/dashboard.html', {
        'users': User.objects.exclude(pk=request.user.pk).order_by('username'),
        'groups': ChatGroup.objects.prefetch_related('members').order_by('name'),
        'group_form': form,
        'active_user': None,
        'active_group': None,
        'is_active_group_member': False,
        'private_messages': Message.objects.none(),
        'group_messages': Message.objects.none(),
    })


@login_required
@require_POST
def join_group(request, slug):
    dashboard_url = reverse('realtime_chat:dashboard')
    group = get_object_or_404(ChatGroup, slug=slug)
    group.members.add(request.user)
    messages.success(request, f'You joined "{group.name}".')
    return redirect(f'{dashboard_url}?group={group.slug}')


@login_required
@require_POST
def leave_group(request, slug):
    group = get_object_or_404(ChatGroup, slug=slug)
    group.members.remove(request.user)
    messages.info(request, f'You left "{group.name}".')
    return redirect('realtime_chat:dashboard')


@login_required
@require_GET
def private_history(request, username):
    other_user = get_object_or_404(User, username=username)
    messages_qs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user)
        | Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver')
    return JsonResponse({'messages': [_serialize_message(message, request.user) for message in messages_qs]})


@login_required
@require_GET
def group_history(request, slug):
    group = get_object_or_404(ChatGroup.objects.prefetch_related('members'), slug=slug)
    if not group.members.filter(pk=request.user.pk).exists():
        raise Http404('You are not a member of this group.')
    return JsonResponse({'messages': [_serialize_message(message, request.user) for message in group.messages.select_related('sender', 'group')]})


def _serialize_message(message, current_user):
    return {
        'id': message.id,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'sender': message.sender.username,
        'is_own_message': message.sender_id == current_user.id,
        'receiver': message.receiver.username if message.receiver_id else None,
        'group': message.group.name if message.group_id else None,
    }
