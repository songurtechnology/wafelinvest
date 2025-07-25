// main.js - WafelInvest Projesine Özel JS

document.addEventListener('DOMContentLoaded', function () {
    // Bootstrap bileşenleri için JS hazır
    // Örnek: Alert kapanış sonrası loglama (gerekirse)
    
    var alertList = document.querySelectorAll('.alert');
    alertList.forEach(function(alert) {
        alert.addEventListener('closed.bs.alert', function () {
            console.log('Alert kapatıldı.');
        });
    });

    // Menü toggler için ekstra kod gerekirse buraya ekle

    // Gelecekte ekleyeceğin tüm custom JS kodları buraya yazılabilir
});
