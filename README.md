# Block Blast Canlı

Telefonda oynanan Block Blast'ın ekranını bilgisayardan okuyan, her tur için en iyi hamle sırasını hesaplayan ve istenirse parçaları fareyle kendisi yerleştiren bir yardımcı.

> Resmi bir uygulama değildir. Block Blast ve geliştiricisiyle hiçbir bağlantısı yoktur. Oyunun dosyalarını, kodunu ya da verilerini değiştirmez; sadece ekrana bakar ve fareyi hareket ettirir. Otomatik oynatma oyunun kullanım şartlarına aykırı olabilir ve hesabının kısıtlanmasına yol açabilir. Kullanım sorumluluğu kullanana aittir.

## Ne yapar

- **Ekranı okur.** Yansıtılan telefon penceresinde 8×8 tahtayı ve alttaki üç parçayı renklerinden tanır.
- **Hamle hesaplar.** Üç parçanın bütün sıralarını ve tahtadaki bütün yerleşimlerini dener. Silinen çizgileri, art arda silme bonusunu ve tur sonunda tahtanın ne kadar temiz kaldığını puanlar: tek kalmış boş kareler, pürüzlü kenarlar, 3×3 ve 5'lik parçalara yer kalıp kalmadığı.
- **Gösterir.** Hamleleri görüntünün üstüne 1-2-3 diye çizer, istenirse Türkçe sesli okur.
- **Otomatik oynar (isteğe bağlı).** Parçayı fareyle tutar, oyunun parçayı nerede gösterdiğini görüntüden izleyip hedefe oturtur, sonra bırakır. Parçanın parmağa göre ne kadar kaydığını oynadıkça öğrenir.

## Gerekenler

- Windows 10 veya 11
- Python 3.8 veya üstü (ek paket gerekmez)
- Chrome, Edge ya da Opera gibi Chromium tabanlı bir tarayıcı
- Telefon ekranını bilgisayara yansıtan bir uygulama. Otomatik oynama, Windows'un **Telefon Bağlantısı** (Phone Link) ile denendi. Fare tıklamalarını telefona dokunma olarak ileten başka yansıtma uygulamaları da çalışabilir.

## Kullanım

1. `baslat.bat` dosyasına çift tıkla. Sayfa tarayıcıda `http://localhost:8765` adresinde açılır. Açılan siyah pencere oynadığın sürece açık kalmalı.
2. Telefon ekranını yansıt ve Block Blast'ı aç. Tarayıcıyı ve telefon penceresini yan yana koy; birbirinin üstüne binmesinler.
3. **Ekranı paylaş**'a bas ve telefon penceresini seç.
4. Görüntüde fareyle sürükleyerek önce 8×8 tahtanın dış kenarını, sonra üç parçanın durduğu şeridi çerçevele. Çerçeveler kaydedilir.
5. Hamleler sağ tarafta ve görüntünün üstünde çıkar.
6. Kendi oynatmak istersen önce **Fareyi test et** ile farenin doğru parçaya ve doğru yere gittiğini gör, sonra **Otomatik oyna**'ya bas.

**Durdurmak için Esc.** Esc her an fareyi bırakır ve otomatik oynamayı durdurur. Bir sorun olursa fare tuşu en geç 4 saniye içinde kendiliğinden bırakılır.

Sadece hamle önerisi istiyorsan Python'a gerek yok: `block-blast-canli.html` dosyasını doğrudan tarayıcıda açman yeterli. Otomatik oynama bu durumda kapalı kalır.

## Sorun giderme

| Belirti | Ne yapmalı |
| --- | --- |
| Boş kareler dolu görünüyor (beyaz nokta var) | Algılama ayarlarında **tahta hassasiyetini** artır |
| Dolu kareler kaçıyor | Tahta hassasiyetini azalt |
| Parçalar yanlış boyutta okunuyor | **Parça ölçeğini sıfırla**; ekranda 3'lü ya da 5'li bir parça varken yeniden öğrenir |
| Parça hep yanlış yere bırakılıyor | **Kaydırmayı sıfırla**, sonra çerçeveleri kontrol et |
| "Bot programına ulaşılamadı" | `baslat.bat` penceresi kapanmış; yeniden aç |

## Nasıl çalışır

| Dosya | Görevi |
| --- | --- |
| `block-blast-canli.html` | Ekran paylaşımı, tahta ve parça algılama, hamle arama, ekran üstü çizim, otomatik oynama mantığı |
| `blockblast_bot.py` | Sayfayı yerel olarak sunar ve sayfanın istediği fare hareketlerini Windows'a iletir |
| `baslat.bat` | Bot programını çift tıkla başlatır |

Tahta iki 32 bitlik sayıdan oluşan bir bit tahtası olarak tutulur. Böylece her yerleştirme ve çizgi silme birkaç bit işlemiyle hesaplanır ve bir turda yüz binlerce olasılık tarayıcıda bir saniyenin altında denenebilir.

Bot programı sadece bu bilgisayardan (`127.0.0.1`) erişilebilir. Fare komutları, her açılışta yeniden üretilen ve sadece kendi sunduğu sayfaya verdiği bir anahtar ister. Başka web siteleri fareni hareket ettiremez.

## Lisans

MIT. Ayrıntılar için `LICENSE` dosyasına bak.
