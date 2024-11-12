from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.views import PasswordChangeView, LogoutView, LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.views.generic import UpdateView
from django.contrib.auth.models import User

from django import forms
from .models import UserSettings

from .middleware import get_session_language

from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm

from django.utils.translation import gettext_lazy as _

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        # exclude = ('password', 'date_joined', 'last_login', 'is_staff', 'is_superuser', 'is_active')
        exclude = ('password',)

class UserUpdateView(UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'registration/edit_profile.html'
    success_url = reverse_lazy('profile')  # Перенаправление на главную страницу после успешного обновления

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile successfully updated!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lng_sel = {'language': get_session_language(self.request), 'url': 'edit_profile', 'params': '?', 'id': 0}
        context['lng'] = lng_sel
        # context['form'] = CustomUserChangeForm(instance=self.request.user)
        return context

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs.update({'initial': self.get_initial()})
    #     return kwargs

    # def get_initial(self):
    #     initial = super().get_initial()
    #     initial['username'] = self.request.user.username
    #     initial['email'] = self.request.user.email
    #     initial['first_name'] = self.request.user.first_name
    #     initial['last_name'] = self.request.user.last_name
    #     return initial

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        # fields = ['language', 'age', 'ai_usage', 'page_size', 'page_buttons', 'model_name', 'model_temp', 'model_top_p']
        fields = ['language', 'age', 'page_size', 'page_buttons']
        labels = {
            'language': _('Language'),
            'age': _('Age'),
            'page_size': _('Items per page'),
            'page_buttons': _('Pagination buttons'),
        }

    def __init__(self, *args, **kwargs):
        dynamic_choices = kwargs.pop('model_choices', [])  # Получаем значения из kwargs
        super().__init__(*args, **kwargs)
        # Устанавливаем поле ai_usage как только для чтения
        # self.fields['ai_usage'].disabled = True
        # self.fields['model_name'].widget = forms.Select(choices=dynamic_choices)

class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def get_context_data(self, **kwargs):
        # Получаем стандартный контекст
        context = super().get_context_data(**kwargs)
        lng_sel = {'language': get_session_language(self.request), 'url': 'signup', 'params': '?', 'id': 0}
        context['lng'] = lng_sel
        return context
    
class CustomLogoutView(LogoutView):
    template_name = 'registration/logged_out1.html'

    def get_context_data(self, **kwargs):
        # Получаем стандартный контекст
        context = super().get_context_data(**kwargs)
        lng_sel = {'language': get_session_language(self.request), 'url': 'login', 'params': '?', 'id': 0}
        context['lng'] = lng_sel
        return context
    
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_context_data(self, **kwargs):
        # Получаем стандартный контекст
        context = super().get_context_data(**kwargs)
        lng_sel = {'language': get_session_language(self.request), 'url': 'login', 'params': '?', 'id': 0}
        context['lng'] = lng_sel
        return context

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change_form1.html'

    def get_context_data(self, **kwargs):
        # Получаем стандартный контекст
        context = super().get_context_data(**kwargs)
        lng_sel = {'language': get_session_language(self.request), 'url': 'password_change', 'params': '?', 'id': 0}
        context['lng'] = lng_sel
        return context
