RANCANG BANGUN PENYARING DIGITAL BUTTERWORTH UNTUK MENGURANGI GANGGUAN PADA SINYAL ELEKTROMIOGRAFI SEBAGAI MASUKAN SISTEM REHABILITASI TANGAN

Ardhya Novri Ramadhan1\*), Achmad Hidayatno2 dan Ir. Sumardi3

1Departemen Teknik Elektro, Fakultas Teknik, Universitas Diponegoro, Semarang, Indonesia

*\*Penulis korespondensi, E-mail: ardhyasan@gmail.com*

Abstrak

Stroke dapat menurunkan fungsi motorik tangan sehingga diperlukan latihan rehabilitasi yang melibatkan usaha aktif pengguna. Sinyal elektromiografi permukaan dapat digunakan sebagai masukan kendali, tetapi amplitudonya kecil dan mudah dipengaruhi artefak gerakan, gangguan frekuensi tinggi, serta interferensi jala-jala listrik. Penelitian ini merancang, mengimplementasikan, dan mengevaluasi subsistem pemrosesan sinyal elektromiografi pada mikrokontroler STM32F411CEU6 sebagai penyedia masukan sistem rehabilitasi tangan. Sinyal dari modul DFRobot SEN0240 dicuplik pada frekuensi nominal 4.000 Hz, dikoreksi nilai tengahnya, kemudian diproses dengan penyaring lolos tinggi Butterworth 20 Hz, penyaring lolos rendah Butterworth 500 Hz, dan penyaring takik 50 Hz dengan faktor kualitas 30. Fitur root mean square dan mean absolute value dihitung setiap 100 ms serta dikirim ke antarmuka melalui UART. Pada sesi kontinu 602,10 detik, sistem menghasilkan 5.901 pembaruan fitur unik tanpa pencacah hilang, kesalahan pemrosesan, atau clipping. Pada 24 rekaman, respons eksperimen Butterworth sebesar -3,02 ± 0,16 dB pada 20 Hz dan -3,01 ± 0,03 dB pada 500 Hz, mendekati respons teoritis -3,01 dB. Penyaring takik menghasilkan pelemahan 2,15 ± 0,05 dB pada interferensi 51 Hz, tetapi hampir tidak melemahkan harmonik 102 Hz. RMS dan MAV memiliki korelasi 0,994, sedangkan 1.420 data UART diterima tanpa kehilangan urutan. Hasil menunjukkan bahwa subsistem mampu melakukan akuisisi, penyaringan, ekstraksi fitur, dan telemetri sesuai rancangan. Pengujian menggunakan satu subjek pada lengan kiri tanpa stimulasi listrik aktif. Hasilnya mendukung penyediaan data masukan, sedangkan kinerja kendali terintegrasi dan pengurangan artefak stimulasi belum dievaluasi.

Kata kunci: elektromiografi, penyaring digital Butterworth, penyaring takik, STM32F411CEU6, rehabilitasi tangan

Abstract

Stroke can impair hand motor function, creating a need for rehabilitation exercises that involve the user's active effort. Surface electromyography can provide a control input, but its low-amplitude signal is susceptible to motion artifacts, high-frequency noise, and power-line interference. This study designs, implements, and evaluates an electromyography signal-processing subsystem on an STM32F411CEU6 microcontroller to provide input data for a hand-rehabilitation system. The signal from a DFRobot SEN0240 module is sampled at a nominal rate of 4,000 Hz, offset-corrected, and processed by a 20 Hz Butterworth high-pass filter, a 500 Hz Butterworth low-pass filter, and a 50 Hz notch filter with a quality factor of 30. Root mean square and mean absolute value features are calculated every 100 ms and transmitted to the interface through UART. During a 602.10 s continuous session, the system produced 5,901 unique feature updates with no missing counters, processing errors, or clipping. Across 24 recordings, the experimental Butterworth response was -3.02 ± 0.16 dB at 20 Hz and -3.01 ± 0.03 dB at 500 Hz, close to the theoretical -3.01 dB response. The notch filter attenuated 51 Hz interference by 2.15 ± 0.05 dB but provided almost no attenuation at the 102 Hz harmonic. RMS and MAV were correlated at 0.994, while 1,420 UART data packets were received without sequence loss. The subsystem therefore performed acquisition, filtering, feature extraction, and telemetry as designed. Testing involved one participant and the left forearm without active electrical stimulation. The results support input-data provision, while integrated control performance and stimulation-artifact suppression remain unevaluated.

Keywords: electromyography, Butterworth digital filter, notch filter, STM32F411CEU6, hand rehabilitation

1. Pendahuluan

Stroke dapat menurunkan kemampuan gerak dan kemandirian. Pada 2021, stroke menjadi penyebab kematian dan disabilitas ketiga di dunia, dengan sekitar 93,8 juta kasus dan 11,9 juta kasus baru [1]. Hemiparesis pada tangan dapat mengganggu aktivitas sehari-hari seperti menggenggam, menulis, makan, dan berpakaian.

Rehabilitasi motorik memerlukan latihan berulang dan terarah yang melibatkan usaha pengguna. *Functional electrical stimulation* (FES) dapat dipadukan dengan elektromiografi permukaan agar stimulasi dipicu oleh usaha gerak, bukan diberikan terus-menerus [2], [3]. Dalam sistem kelompok, penelitian ini terbatas pada akuisisi dan pemrosesan EMG; stimulator, algoritma kendali, dan perancangan antarmuka pengguna berada di luar ruang lingkup.

Amplitudo sinyal elektromiografi permukaan (*sEMG*) umumnya berada pada orde mikrovolt hingga milivolt rendah dan memiliki spektrum energi fisiologis pada rentang 20–500 Hz [4], sehingga sangat rentan terdistorsi oleh artefak gerak kabel (<20 Hz), interferensi jala-jala listrik 50 Hz, derau frekuensi tinggi, maupun artefak stimulasi [5], [6], [7]. Mutu pengondisian sinyal analog dan arsitektur pemrosesan digital pada mikrokontroler merupakan faktor kunci untuk menjaga integritas komponen spektral daya serta keandalan fitur EMG [8]. Sinyal karena itu perlu dibatasi pada rentang frekuensi yang relevan dan interferensi 50 Hz ditekan secara selektif dengan mempertimbangkan komponen sEMG yang ikut teredam.

Penelitian ini merancang, menerapkan, dan mengevaluasi penyaring digital Butterworth sebagai bagian subsistem penyedia masukan sistem rehabilitasi tangan. Rantai pemrosesan pada STM32F411CEU6 mencakup akuisisi nominal 4 kHz, koreksi *offset*, kaskade Butterworth 20–500 Hz, penyaring takik 50 Hz, ekstraksi RMS dan MAV, serta pengiriman RMS melalui UART. Evaluasi menggunakan pasangan data sebelum dan sesudah penyaringan yang direkam sinkron, respons frekuensi eksperimen, perubahan fitur, dan kontinuitas telemetri. Pengujian dilakukan tanpa FES aktif sehingga hasil tidak digunakan untuk menyimpulkan penghilangan artefak stimulasi, kinerja kendali terintegrasi, atau manfaat klinis.

2. Metode

2.1. Perancangan Arsitektur Subsistem dan Ruang Lingkup

Modul DFRobot SEN0240 mengubah aktivitas listrik otot menjadi tegangan analog yang dibaca oleh ADC1 pada pin PA0 STM32F411CEU6 [9], [10]. Prinsip lokasi dan orientasi elektroda permukaan dibahas dalam [11]. Rantai pemrosesan terdiri atas kalibrasi dan koreksi *offset*, HPF Butterworth 20 Hz, LPF Butterworth 500 Hz, takik 50 Hz, perhitungan RMS dan MAV pada jendela 100 ms, serta pengiriman RMS terfilter melalui UART. GUI digunakan sebagai penerima untuk validasi data dan penghalusan EMA; ketepatan keputusan kendali, kalibrasi *maximum voluntary contraction*, dan performa stimulator tidak dievaluasi.

![Diagram blok rantai pemrosesan sinyal EMG dari sensor hingga GUI](data:image/jpeg;base64...)

Gambar 1. Alur akuisisi, pemrosesan digital, telemetri, dan penyajian sinyal EMG.

Tabel 1. Parameter utama implementasi subsistem EMG.

| **Parameter** | **Nilai** |
| --- | --- |
| Sensor dan masukan | SEN0240; ADC1/PA0 |
| ADC | 12 bit; 3,3 V; 0,806 mV/LSB |
| Frekuensi pencuplikan | 4.000 Hz nominal |
| Kalibrasi *offset* | 8.000 sampel; 2 s |
| HPF Butterworth | 20 Hz; orde 2 |
| LPF Butterworth | 500 Hz; orde 2 |
| Penyaring takik | 50 Hz; orde 2; Q = 30 |
| Ekstraksi fitur | 400 sampel; 100 ms; tanpa *overlap* |

2.2. Akuisisi, Koreksi Offset, dan Penyaringan Digital

SEN0240 diberi catu 3,3 V dan menghasilkan tegangan sekitar 0–3,0 V. ADC 12 bit menyediakan 4.096 tingkat, setara resolusi sekitar 0,806 mV/LSB. Frekuensi pencuplikan nominal 4.000 Hz memberikan interval 0,25 ms, frekuensi Nyquist 2.000 Hz, dan delapan sampel per periode pada batas atas 500 Hz. Nilai *offset* diperoleh sebagai rata-rata 8.000 sampel selama 2 s pada kondisi relaks, kemudian dikurangkan dari sampel berikutnya.

|  |  |
| --- | --- |
| *x[n] = vADC[n] − v̄offset* | (1) |

Tahap pembatas pita terdiri atas HPF orde 2 pada 20 Hz dan LPF orde 2 pada 500 Hz yang direalisasikan sebagai kaskade dua *biquad* IIR presisi *floating-point 32 bit [12], [13]*. Kaskade tersebut mempunyai orde efektif empat. Butterworth dipilih karena memiliki karakteristik respons magnitudo maksimal-datar (*maximally flat*) pada pita lewat tanpa ripple [14]. Tahap berikutnya adalah takik IIR orde 2 pada 50 Hz dengan Q = 30 dan perkiraan lebar pita 1,67 Hz. Karena takik bersifat sempit dan berfrekuensi tetap, redamannya menurun apabila interferensi bergeser dari frekuensi pusat.

|  |  |
| --- | --- |
| *y[n] = b0x[n] + b1x[n−1] + b2x[n−2] − a1y[n−1] − a2y[n−2]* | (2) |

![Kurva respons frekuensi HPF, LPF, notch, dan kaskade total](data:image/png;base64...)

Gambar 2. Respons frekuensi teoritis filter digital yang diimplementasikan pada *firmware*.

2.3. Ekstraksi Fitur RMS/MAV dan Telemetri UART

Setiap 400 sampel membentuk satu jendela tanpa overlap dengan durasi nominal 100 ms dan laju pembaruan nominal 10 Hz. RMS dan MAV merangkum amplitudo sinyal yang dipengaruhi aktivitas unit motorik serta kondisi perekaman [15], [16]. RMS digunakan sebagai keluaran utama aktivitas relatif, sedangkan MAV menjadi pembanding pola amplitudo. Keduanya tidak dikalibrasi terhadap gaya genggaman. Untuk jendela N sampel, kedua fitur dihitung dengan (3) dan (4).

|  |  |
| --- | --- |
| *RMS = √[(1/N) Σ x²[n]]* | (3) |
| *MAV = (1/N) Σ |x[n]|* | (4) |

Nilai RMS terfilter dalam milivolt dikirim melalui UART dengan *payload* EMG\_RMS\_MV. Aplikasi penerima memeriksa nomor urut dan format *payload*, kemudian dapat menerapkan *exponential moving average* untuk penghalusan visual. Jalur ini dipakai untuk memverifikasi kontinuitas penerimaan, bukan untuk menilai algoritma kendali.

2.4. Prosedur Pengujian dan Analisis Data

Pengujian melibatkan penulis sebagai satu-satunya subjek pada lengan bawah kiri. Sesi kontinu satu kali tanpa penghentian perekaman berdurasi 602,10 s digunakan untuk memeriksa kontinuitas fitur, pencacah pembaruan, error, dan clipping. Rekaman mentah berlangsung 2 s pada 4.000 Hz atau 8.000 sampel; data disimpan di *buffer* dan baru dikirim setelah perekaman agar UART tidak mengganggu interval pencuplikan nominal. Dua belas rekaman utama mencakup relaks, ringan, sedang RPE 5, dan kuat, masing-masing tiga pengulangan. Intensitas sedang mengacu pada skala *category-ratio* Borg 0–10 [17]. Durasi jeda antarrekaman raw dan koordinat anatomis pemasangan tidak dicatat secara terukur. Tanpa dinamometer, kategori tersebut hanya menyatakan usaha subjektif relatif. Telemetri dievaluasi pada sesi penerimaan GUI tersendiri.

Sebanyak 24 rekaman mentah lengkap digunakan untuk mengevaluasi respons Butterworth. Fungsi transfer eksperimen dihitung dengan estimator H1 dari pasangan sinyal sinkron setelah koreksi *offset* sebagai masukan dan keluaran HPF+LPF sebagai keluaran [18]. PSD sebelum dan sesudah takik dihitung menggunakan metode Welch dengan jendela Hann 4.000 sampel, *overlap* 50%, dan resolusi 1 Hz [19]. Tiga rekaman relaks dengan interferensi tinggi dipakai khusus untuk karakterisasi takik. Frekuensi pencuplikan aktual, *jitter*, waktu eksekusi, beban prosesor, SNR, gaya genggam absolut, dan respons saat FES aktif tidak diukur.

3. Hasil dan Pembahasan

3.1. Kontinuitas Akuisisi dan Kualitas Data

Sesi 602,10 s menghasilkan 12.043 baris pencatatan dan 5.901 pembaruan fitur unik pada rentang pencacah 20.780–26.680. Tidak ditemukan pencacah hilang, emg\_*error*\_flags tidak nol, atau *clipping*. Interval pencatatan utama sekitar 0,05 s dan pembaruan fitur sekitar 0,10 s. Setiap *raw capture* berisi 8.000 indeks sampel berurutan. Temuan ini mendukung kontinuitas akuisisi dan pemrosesan selama sesi uji, tetapi bukan pengukuran frekuensi pencuplikan aktual, *jitter*, atau beban prosesor.

Tabel 2. Hasil pemeriksaan kontinuitas akuisisi.

| **Indikator** | **Hasil** |
| --- | --- |
| Durasi sesi | 602,10 s |
| Baris pencatatan | 12.043 |
| Pembaruan fitur unik | 5.901 |
| Pencacah hilang | 0 |
| *Error* pemrosesan | 0 |
| *Clipping* | 0 |
| Isi tiap *raw capture* | 8.000 sampel berurutan |

3.2. Respons Penyaring Butterworth

Pada sesi kontinu, setelah HPF+LPF, MAV rata-rata turun dari 9,32 menjadi 8,71 mV (6,55%), sedangkan RMS rata-rata turun dari 12,67 menjadi 11,25 mV (11,24%). Pada contoh genggaman kuat, RMS turun dari 63,99 menjadi 62,56 mV (2,23%); penurunan pada tiga rekaman relaks mencapai 14–17%, sedangkan pada tiga rekaman kuat 1,7–2,9%. Penurunan fitur tidak menyatakan persentase derau yang dihilangkan. Verifikasi utama menggunakan respons frekuensi 24 rekaman mentah.

Tabel 3. Respons teoritis dan eksperimen kaskade Butterworth.

| **f (Hz)** | **Teori (dB)** | **Eksperimen (dB)** |
| --- | --- | --- |
| 10 | −12,31 | −12,22 ± 0,72 |
| 20 | −3,01 | −3,02 ± 0,16 |
| 50 | −0,11 | −0,10 ± 0,01 |
| 100 | −0,01 | −0,01 ± 0,02 |
| 500 | −3,01 | −3,01 ± 0,03 |
| 750 | −8,90 | −8,91 ± 0,08 |
| 1.000 | −15,44 | −15,41 ± 0,23 |

Pada batas 20 dan 500 Hz, hasil eksperimen masing-masing −3,02 ± 0,16 dB dan −3,01 ± 0,03 dB, hampir sama dengan respons teoritis −3,01 dB. Di pita lewat 50–100 Hz, redaman berada dekat 0 dB; di luar pita, redaman meningkat. Hasil ini memverifikasi implementasi digital pada *firmware*, bukan respons gabungan elektroda, pengondisi analog SEN0240, dan filter digital.

![Waveform raw centered, band-pass, dan keluaran setelah notch](data:image/png;base64...)

Gambar 3. Perbandingan sinyal sinkron pada setiap tahap penyaringan untuk contoh genggaman kuat.

3.3. Kinerja Penyaring Takik

Setelah takik, MAV rata-rata berubah dari 8,71 menjadi 7,95 mV (turun 8,77%) dan RMS dari 11,25 menjadi 10,45 mV (turun 7,10%). Pada tiga rekaman interferensi, komponen dominan berada sekitar 51 Hz dan harmoniknya sekitar 102 Hz. Pelemahan pada 51 Hz sebesar 2,15; 2,21; dan 2,10 dB, dengan rata-rata 2,15 ± 0,05 dB, dekat dengan respons teoritis 2,33 dB pada frekuensi tersebut. Pada 102 Hz, pelemahan eksperimen hanya 0,00197 dB dan respons teoritis 0,00200 dB.

Tabel 4. Ringkasan perubahan setelah penyaring takik.

| **Indikator** | **Sebelum** | **Sesudah/Redaman** |
| --- | --- | --- |
| MAV rata-rata | 8,71 mV | 7,95 mV (−8,77%) |
| RMS rata-rata | 11,25 mV | 10,45 mV (−7,10%) |
| Interferensi 51 Hz | — | 2,15 ± 0,05 dB |
| Harmonik 102 Hz | — | 0,00197 dB |

![PSD Welch yang menunjukkan komponen sekitar 51 Hz dan harmonik 102 Hz](data:image/png;base64...)

Gambar 4. PSD sebelum dan sesudah takik pada kondisi interferensi listrik.

Hasil tersebut konsisten dengan sifat takik Q = 30 yang sempit dan berfrekuensi tetap. Pada skala frekuensi nominal, komponen 51 Hz memperoleh redaman lebih kecil daripada pusat takik 50 Hz, sedangkan satu takik tidak menekan harmonik 102 Hz. Posisi puncak dihitung dengan sampling nominal dan resolusi spektrum 1 Hz. Karena sampling aktual belum diukur, puncak tersebut tidak memastikan pergeseran frekuensi sumber listrik. Hasil juga tidak menyatakan penghilangan seluruh gangguan atau artefak stimulasi.

3.4. Karakteristik RMS/MAV dan Variasi Aktivitas Otot

Pada seluruh fitur, MAV mempunyai rata-rata 7,95 mV, median 4,12 mV, minimum 2,18 mV, maksimum 112,34 mV, dan simpangan baku 8,72 mV. RMS mempunyai rata-rata 10,45 mV, median 4,84 mV, minimum 2,68 mV, maksimum 142,08 mV, dan simpangan baku 12,02 mV. RMS dan MAV berkorelasi sangat kuat (r = 0,994; R² = 0,988), yang menunjukkan kesamaan pola amplitudo, bukan validasi terhadap gaya atau ukuran fisiologis independen.

![Scatter plot MAV terhadap RMS dengan regresi linier](data:image/png;base64...)

Gambar 5. Hubungan MAV dan RMS hasil akhir pemrosesan sinyal EMG.

Tabel 5. Nilai RMS pada variasi aktivitas otot.

| **Kondisi** | **Tiap pengulangan (mV)** | **Rata-rata ± SD** | **CV** |
| --- | --- | --- | --- |
| Relaks | 6,99; 7,99; 7,93 | 7,64 ± 0,56 | 7,3% |
| Ringan | 20,45; 12,74; 15,12 | 16,10 ± 3,95 | 24,5% |
| Sedang RPE 5 | 37,53; 36,82; 41,22 | 38,52 ± 2,36 | 6,1% |
| Kuat | 61,85; 35,11; 61,17 | 52,71 ± 15,25 | 28,9% |

![Grafik titik tiap pengulangan dan rata-rata plus simpangan baku](data:image/png;base64...)

Gambar 6. Sebaran dan rata-rata RMS pada empat kondisi genggaman.

Rata-rata RMS meningkat dari 7,64 mV saat relaks menjadi 52,71 mV pada genggaman kuat. Namun, pengulangan kuat kedua 35,11 mV tumpang tindih dengan rentang sedang 36,82–41,22 mV. Dengan instruksi subjektif, tanpa dinamometer, dan hanya tiga pengulangan, hasil hanya mendukung kecenderungan relatif; data tidak digunakan untuk mengklaim klasifikasi tingkat genggaman tervalidasi atau gaya absolut.

Pada tiga jendela perubahan posisi (496–506 s, 531–541 s, dan 557–567 s), MAV sebesar 27,69 ± 0,26 mV dan RMS 38,51 ± 0,95 mV, dengan CV masing-masing 0,95% dan 2,47%. Karena data IMU tidak direkam sinkron, hubungan EMG dengan sudut tangan tidak dapat dinilai.

3.5. Telemetri dan Evaluasi Keseluruhan

GUI menerima 1.420 data bernomor 95–1.514 tanpa kehilangan urutan, dengan interval median 0,098 s dan nol *payload* gagal *parsing*. Pada 58,91 s, RMS 107,86 mV menghasilkan EMA 72,91 mV, menunjukkan penghalusan perubahan sesaat. Hasil ini memverifikasi kontinuitas jalur UART dan penerimaan GUI, bukan akurasi keputusan kendali, latensi kendali, atau efektivitas rehabilitasi.

Tabel 6. Hasil pengujian telemetri UART.

| **Indikator** | **Hasil** |
| --- | --- |
| *Payload* | EMG\_RMS\_MV |
| Jumlah data | 1.420 |
| Rentang nomor urut | 95–1.514 |
| Urutan hilang | 0 |
| Interval median | 0,098 s |
| Gagal *parsing* | 0 |

Secara keseluruhan, subsistem menunjukkan kesesuaian dengan rancangan pada aspek kontinuitas akuisisi, bentuk respons Butterworth, selektivitas takik, ekstraksi fitur, dan pengiriman data. Bukti tersebut tetap dibatasi pada konfigurasi nominal dan sesi pengujian yang tersedia. Validasi berikutnya perlu mengukur frekuensi pencuplikan aktual, *jitter*, beban prosesor, latensi jalur kendali, SNR, serta respons saat FES aktif menggunakan protokol keselamatan dan etik yang sesuai.

4. Kesimpulan

Penyaring digital Butterworth telah diimplementasikan dalam subsistem penyedia masukan sistem rehabilitasi tangan berbasis STM32F411CEU6. Subsistem menjalankan akuisisi 4 kHz nominal, koreksi *offset*, kaskade Butterworth 20–500 Hz, takik 50 Hz, ekstraksi RMS/MAV setiap 100 ms, dan telemetri UART sesuai rancangan. Pada sesi 602,10 s diperoleh 5.901 pembaruan fitur unik tanpa pencacah hilang, *error*, atau *clipping*. Respons eksperimen Butterworth pada 24 rekaman mencapai −3,02 ± 0,16 dB pada 20 Hz dan −3,01 ± 0,03 dB pada 500 Hz, sangat dekat dengan respons teoritis −3,01 dB. Takik Q = 30 melemahkan interferensi 51 Hz sebesar 2,15 ± 0,05 dB, tetapi hampir tidak memengaruhi harmonik 102 Hz. RMS dan MAV mengikuti pola serupa dengan r = 0,994, sedangkan rata-rata RMS meningkat dari 7,64 mV saat relaks menjadi 52,71 mV pada genggaman kuat meskipun terjadi tumpang tindih antar-pengulangan. Sebanyak 1.420 paket UART diterima tanpa kehilangan urutan. Hasil pada satu subjek mendukung pemrosesan dan pengiriman aktivitas otot relatif sebagai data masukan. Pengujian tanpa FES aktif belum membuktikan pengurangan artefak stimulasi, kinerja kendali terintegrasi, atau manfaat klinis.

Referensi

1. GBD 2021 Stroke Risk Factor Collaborators, “Global, regional, and national burden of stroke and its risk factors, 1990–2021: a systematic analysis for the Global Burden of Disease Study 2021,” The Lancet Neurology, vol. 23, no. 10, pp. 973–1003, 2024, doi: 10.1016/S1474-4422(24)00369-7.
2. M. A. Khan, H. Fares, H. Ghayvat, I. C. Brunner, S. Puthusserypady, B. Razavi, M. Lansberg, A. Poon, and K. J. Meador, “A systematic review on functional electrical stimulation based rehabilitation systems for upper limb post-stroke recovery,” Frontiers in Neurology, vol. 14, Art. no. 1272992, 2023, doi: 10.3389/fneur.2023.1272992.
3. F. Rossi, P. Motto Ros, R. M. Rosales, and D. Demarchi, “Embedded Bio-Mimetic System for Functional Electrical Stimulation Controlled by Event-Driven sEMG,” Sensors, vol. 20, no. 5, Art. no. 1535, 2020, doi: 10.3390/s20051535.
4. L. McManus, G. De Vito, and M. M. Lowery, “Analysis and Biophysics of Surface EMG for Physiotherapists and Kinesiologists: Toward a Common Language With Rehabilitation Engineers,” Frontiers in Neurology, vol. 11, Art. no. 576729, 2020, doi: 10.3389/fneur.2020.576729.
5. M. B. I. Reaz, M. S. Hussain, and F. Mohd-Yasin, “Techniques of EMG signal analysis: detection, processing, classification and applications,” Biological Procedures Online, vol. 8, no. 1, pp. 11–35, 2006, doi: 10.1251/bpo115.
6. K. Li, J. Zhang, L. Wang, M. Zhang, J. Li, and S. Bao, “A review of the key technologies for sEMG-based human-robot interaction systems,” Biomedical Signal Processing and Control, vol. 62, Art. no. 102074, 2020, doi: 10.1016/j.bspc.2020.102074.
7. F. Mandrile, D. Farina, M. Pozzo, and R. Merletti, “Stimulation artifact in surface EMG signal: effect of the stimulation waveform, detection system, and current amplitude using hybrid stimulation technique,” IEEE Transactions on Neural Systems and Rehabilitation Engineering, vol. 11, no. 4, pp. 407–415, 2003, doi: 10.1109/TNSRE.2003.819791.
8. T. Roland, S. Amsuess, M. F. Russold, and W. Baumgartner, “Ultra-Low-Power Digital Filtering for Insulated EMG Sensing,” Sensors, vol. 19, no. 4, Art. no. 959, 2019, doi: 10.3390/s19040959.
9. DFRobot, “Gravity: Analog EMG Sensor by OYMotion (SEN0240),” DFRobot Wiki/Product Documentation. [Online]. Available: https://wiki.dfrobot.com/SEN0240. [Accessed: 7-Jun-2026].
10. STMicroelectronics, “STM32F411xC STM32F411xE Arm Cortex-M4 32b MCU+FPU, 125 DMIPS, 512 KB Flash, 128 KB RAM, USB OTG FS, 11 TIMs, 1 ADC, 13 communication interfaces,” Datasheet DS10314 Rev. 8, Jan. 2024. [Online]. Available: https://www.st.com/resource/en/datasheet/stm32f411ce.pdf. [Accessed: 7-Jun-2026].
11. H. J. Hermens, B. Freriks, C. Disselhorst-Klug, and G. Rau, “Development of recommendations for SEMG sensors and sensor placement procedures,” Journal of Electromyography and Kinesiology, vol. 10, no. 5, pp. 361–374, 2000, doi: 10.1016/S1050-6411(00)00027-4.
12. A. V. Oppenheim and R. W. Schafer, Discrete-Time Signal Processing, 3rd ed. Upper Saddle River, NJ, USA: Pearson, 2010.
13. J. G. Proakis and D. G. Manolakis, Digital Signal Processing: Principles, Algorithms, and Applications, 4th ed. Upper Saddle River, NJ, USA: Pearson, 2007.
14. S. Butterworth, “On the theory of filter amplifiers,” Experimental Wireless and the Wireless Engineer, vol. 7, pp. 536–541, Oct. 1930.
15. D. Staudenmann, K. Roeleveld, D. F. Stegeman, and J. H. van Dieën, “Methodological aspects of SEMG recordings for force estimation—A tutorial and review,” Journal of Electromyography and Kinesiology, vol. 20, no. 3, pp. 375–387, 2010, doi: 10.1016/j.jelekin.2009.08.005.
16. C. J. De Luca, A. Adam, R. Wotiz, L. D. Gilmore, and S. H. Nawab, “Decomposition of surface EMG signals,” Journal of Neurophysiology, vol. 96, no. 3, pp. 1646–1657, 2006, doi: 10.1152/jn.00009.2006.
17. G. Borg, Borg's Perceived Exertion and Pain Scales. Champaign, IL, USA: Human Kinetics, 1998.
18. J. S. Bendat and A. G. Piersol, Random Data: Analysis and Measurement Procedures, 4th ed. Hoboken, NJ, USA: Wiley, 2010, doi: 10.1002/9781118032428.
19. P. D. Welch, “The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms,” IEEE Transactions on Audio and Electroacoustics, vol. AU-15, no. 2, pp. 70–73, 1967, doi: 10.1109/TAU.1967.1161901.