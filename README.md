# sMusic-core
### Elementy systemu odtwarzające muzykę

### Czym jest sMusic
sMusic jest oprogramowaniem udostępnionym na licencji ruchu wolnego oprogramowania służącym do zdalnego sterowania szkolnym radiowęzłem przez aplikację webową dostosowaną do urządzeń mobilnych.

### Czym jest sMusic-core
sMusic-core jest komponentem systemu sMusic działającym na komputerze podłączonym do głośników (dokładniejszy opis jest dostępny na [wiki](https://github.com/mRokita/sMusic-core/wiki). Dopełnieniem jego funkcji jest frontend, [sMusic-www](https://github.com/mRokita/sMusic-www/).

### Instalacja
```
git clone https://github.com/mRokita/sMusic-core/
cd sMusic-core
sudo python setup.py install
vim /etc/sMusic/client.ini #Edycja configu, dokumentacja na ten temat pojawi się w przyszłości
systemctl start sMusicClient
```
### Zrzuty ekranu
![screenshot](https://sc-cdn.scaleengine.net/i/6c6986f03056276509f08d369866f22f.png)
