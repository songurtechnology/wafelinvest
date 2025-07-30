import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Investment, PaymentConfirmation


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email adresinizi girin',
            'class': 'form-control',
            'autocomplete': 'email',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Kullanıcı adınızı girin',
            'autocomplete': 'username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Şifrenizi girin',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Şifrenizi tekrar girin',
            'autocomplete': 'new-password',
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu email zaten kayıtlı.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Kullanıcı Adı",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kullanıcı adınızı girin',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="Şifre",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifrenizi girin',
            'autocomplete': 'current-password',
        })
    )


class InvestmentForm(forms.ModelForm):
    agreement = forms.BooleanField(
        required=True,
        label='Yatırım şartlarını okudum ve kabul ediyorum.',
        error_messages={'required': 'Lütfen yatırım şartlarını kabul edin.'}
    )

    class Meta:
        model = Investment
        fields = ['agreement']  # ✅ amount is now set via view, not user input
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Yatırım tutarını girin (₺)',
                'min': '1',
                'step': '0.01',
            }),
        }

    def __init__(self, *args, profile=None, package=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile = profile
        self._package = package

        if package:
            self.fields['amount'].initial = package.price
            self.fields['amount'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        agreement = cleaned_data.get('agreement')
        if not agreement:
            self.add_error('agreement', 'Lütfen yatırım şartlarını kabul edin.')

        if self._profile:
            self.instance.profile = self._profile
        if self._package:
            self.instance.package = self._package

        return cleaned_data




class PaymentConfirmationForm(forms.ModelForm):
    class Meta:
        model = PaymentConfirmation
        fields = ['investment', 'payment_screenshot']
        widgets = {
            'investment': forms.HiddenInput(),
            'payment_screenshot': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf',
            }),
        }
        labels = {
            'payment_screenshot': 'Ödeme Dekontu',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['investment'].widget = forms.HiddenInput()

    def clean_payment_screenshot(self):
        file = self.cleaned_data.get('payment_screenshot')
        if file:
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf', 'application/x-pdf']
            if file.content_type not in allowed_types:
                raise forms.ValidationError("Sadece JPG, PNG veya PDF dosyaları yükleyebilirsiniz.")
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Dosya boyutu 5MB'ı geçmemelidir.")
        else:
            raise forms.ValidationError("Ödeme dekontu yüklemek zorunludur.")
        return file