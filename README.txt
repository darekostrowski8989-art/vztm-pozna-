VZTM POZNAŃ — lokalny portal demonstracyjny

Uruchomienie w Windows PowerShell:
1. Otwórz PowerShell w folderze projektu.
2. python -m pip install -r requirements.txt
3. python main.py
4. Otwórz http://127.0.0.1:5000

Konto demonstracyjne:
Login: admin
Hasło: VztmPoznan2026!

Po pierwszym uruchomieniu utworzy się plik vztm.db z danymi.
Zmień hasło demonstracyjne i klucz SECRET przed wdrożeniem publicznym.
To wersja startowa do lokalnych testów; przed publikacją w internecie
należy dodać zarządzanie kontami, uprawnienia, CSRF, kopie zapasowe,
HTTPS i bezpieczny klucz VZTM_SECRET_KEY.
Logo jest autorskim znakiem projektu w pliku static/images/logo.svg.
