![](data:image/jpeg;base64...)

**RANCANG BANGUN TAPIS DIGITAL BUTTERWORTH UNTUK MENGURANGI GANGGUAN PADA SINYAL ELEKTROMIOGRAFI SEBAGAI MASUKAN SISTEM REHABILITASI TANGAN**

**TUGAS AKHIR**

**ARDHYA NOVRI RAMADHAN**

**21060122130096**

**PROGRAM STUDI SARJANA**

**DEPARTEMEN TEKNIK ELEKTRO**

**FAKULTAS TEKNIK**

**UNIVERSITAS DIPONEGORO**

**SEMARANG**

**SEPTEMBER 2026**

![](data:image/jpeg;base64...)

**RANCANG BANGUN TAPIS DIGITAL BUTTERWORTH UNTUK MENGURANGI GANGGUAN PADA SINYAL ELEKTROMIOGRAFI SEBAGAI MASUKAN SISTEM REHABILITASI TANGAN**

**TUGAS AKHIR**

**Diajukan sebagai salah satu syarat untuk memperoleh gelar Sarjana Teknik**

**ARDHYA NOVRI RAMADHAN**

**21060122130096**

**PROGRAM STUDI SARJANA**

**DEPARTEMEN TEKNIK ELEKTRO**

**FAKULTAS TEKNIK**

**UNIVERSITAS DIPONEGORO**

**SEMARANG**

**SEPTEMBER 2026**

# HALAMAN PERNYATAAN ORISINALITAS

**Tugas Akhir ini adalah hasil karya sendiri,**

**dan semua sumber baik yang dikutip maupun yang dirujuk**

**telah saya nyatakan dengan benar.**

| Tanda Tangan | : |
| --- | --- |
| Nama | : Ardhya Novri Ramadhan |
| NIM | : 21060122130096 |
| Tanggal | : 23 Agustus 2026 |

# HALAMAN PERSETUJUAN

Tugas Akhir dengan judul: Rancang Bangun Tapis Digital Butterworth untuk Mengurangi Gangguan pada Sinyal Elektromiografi sebagai Masukan Sistem Rehabilitasi Tangan

| Nama | : Ardhya Novri Ramadhan |
| --- | --- |
| NIM | : 21060122130096 |
| Program Studi | : Sarjana Teknik Elektro |

telah diperiksa dan disetujui oleh dosen pembimbing untuk diajukan dalam sidang Tugas Akhir pada Program Studi Sarjana, Departemen Teknik Elektro, Fakultas Teknik, Universitas Diponegoro.

|  |  |
| --- | --- |
| **Pembimbing I**    Achmad Hidayatno S.T., M.T.  NIP. 196912211995121001 | **Pembimbing II**    Ir. Sumardi S.T., M.T., IPM., ASEAN Eng.  NIP. 196811111994121001 |

# HALAMAN PENGESAHAN

Tugas Akhir ini diajukan oleh:

| Nama | | : Ardhya Novri Ramadhan |
| --- | --- | --- |
| NIM | | : 21060122130096 |
| Departemen/Program Studi | | : Departemen Teknik Elektro / Program Studi Sarjana Teknik Elektro |
| Judul Tugas Akhir |  | : Rancang Bangun Tapis Digital Butterworth untuk Mengurangi Gangguan pada Sinyal Elektromiografi sebagai Masukan Sistem Rehabilitasi Tangan |

Telah berhasil dipertahankan di hadapan Tim Penguji dan diterima sebagai bagian persyaratan yang diperlukan untuk memperoleh gelar Sarjana Teknik pada Program Studi Sarjana, Departemen Teknik Elektro, Fakultas Teknik, Universitas Diponegoro.

**TIM PENGUJI**

| Pembimbing I | : Achmad Hidayatno S.T., M.T. | |
| --- | --- | --- |
| Pembimbing II | : Ir. Sumardi S.T., M.T., IPM., ASEAN Eng. | |
| Penguji I | : | |
| Penguji II | : | |
| Penguji III | : | |
|  | | Semarang, 29 Agustus 2026  Ketua Departemen Teknik Elektro,  Ir. Aghus Sofwan S.T., M.T., Ph.D., IPU  NIP. 197302041997021001 |

# HALAMAN PERNYATAAN PERSETUJUAN PUBLIKASI TUGAS AKHIR UNTUK KEPENTINGAN AKADEMIS

Sebagai sivitas akademika Universitas Diponegoro, saya yang bertanda tangan di bawah ini:

| Nama | : ARDHYA NOVRI RAMADHAN |
| --- | --- |
| NIM | : 21060122130096 |
| Program Studi | : SARJANA (S-1) |
| Departemen | : TEKNIK ELEKTRO |
| Fakultas | : TEKNIK |
| Jenis Karya | : TUGAS AKHIR |

demi pengembangan ilmu pengetahuan, menyetujui untuk memberikan kepada Universitas Diponegoro Hak Bebas Royalti Noneksklusif (*Non-exclusive Royalty-Free Right*) atas karya ilmiah saya yang berjudul:

**“Rancang Bangun Tapis Digital Butterworth untuk Mengurangi Gangguan pada Sinyal Elektromiografi sebagai Masukan Sistem Rehabilitasi Tangan”**

beserta perangkat yang ada (jika diperlukan). Dengan Hak Bebas Royalti Noneksklusif ini, Universitas Diponegoro berhak menyimpan, mengalihmedia/formatkan, mengelola dalam bentuk pangkalan data, merawat, dan memublikasikan Tugas Akhir saya selama tetap mencantumkan nama saya sebagai penulis/pencipta dan pemilik Hak Cipta.

Demikian pernyataan ini saya buat dengan sebenarnya.

Dibuat di : Semarang
Pada tanggal : 24 Agustus 2026

Yang menyatakan,

Ardhya Novri Ramadhan
21060122130096

# ABSTRAK

*Sinyal elektromiografi permukaan dapat menjadi masukan sistem rehabilitasi tangan, tetapi rekamannya dipengaruhi gangguan. Penelitian ini mengimplementasikan dan mengevaluasi subsistem pemrosesan sEMG pada STM32F411CEU6. Keluaran SEN0240 diakuisisi pada konfigurasi nominal 4.000 Hz, dikoreksi offsetnya, lalu diproses oleh Butterworth lolos tinggi 20 Hz, lolos rendah 500 Hz, dan takik 50 Hz dengan Q = 30. RMS dan MAV dihitung setiap 400 sampel. Pengujian menggunakan satu subjek tanpa stimulasi aktif. Sesi kontinu 602,10 detik memuat 5.901 pembaruan fitur unik tanpa celah pencacah, flag kesalahan, atau clipping yang terdeteksi. Pada 24 rekaman raw, respons Butterworth sebesar −3,02 ± 0,16 dB pada 20 Hz dan −3,01 ± 0,03 dB pada 500 Hz menurut skala pencuplikan nominal. Tiga rekaman interferensi menghasilkan pelemahan takik 2,15 ± 0,05 dB pada bin 51 Hz dan sekitar 0,002 dB pada 102 Hz. Pada skala mV ekuivalen masukan ADC, rata-rata RMS meningkat dari 7,64 mV saat relaks menjadi 52,71 mV saat usaha kuat, tetapi urutan kategori tidak konsisten pada setiap pengulangan. Log GUI memuat 1.420 nilai RMS dengan isi numerik konsisten dan interval pencatatan median 0,098 detik. Hasil mendukung kesesuaian respons digital dan penyediaan fitur amplitudo untuk antarmuka data. Ketepatan frekuensi aktual, kehilangan paket pemancar, dan kinerja selama FES aktif belum dinilai.*

***Kata Kunci:*** *elektromiografi, tapis digital Butterworth, tapis takik, STM32F411CEU6, rehabilitasi tangan*

# ABSTRACT

*Surface electromyography can provide input to a hand rehabilitation system, but recorded signals are affected by interference. This study implements and evaluates an sEMG processing subsystem on an STM32F411CEU6. The SEN0240 output is acquired at a nominal sampling configuration of 4,000 Hz, offset-corrected, and processed by a 20 Hz Butterworth high-pass filter, a 500 Hz low-pass filter, and a 50 Hz notch filter with Q = 30. RMS and MAV are calculated every 400 samples. Testing involves one participant without active stimulation. A 602.10 s recording contains 5,901 unique feature updates with no detected counter gaps, error flags, or clipping. Across 24 raw recordings, the Butterworth response is −3.02 ± 0.16 dB at 20 Hz and −3.01 ± 0.03 dB at 500 Hz on the nominal frequency scale. Three interference recordings show notch attenuation of 2.15 ± 0.05 dB at the 51 Hz bin and approximately 0.002 dB at 102 Hz. On the ADC-input-equivalent voltage scale, mean RMS increases from 7.64 mV at rest to 52.71 mV during strong effort, although category ordering is inconsistent across repetitions. The GUI log contains 1,420 RMS values with consistent numeric content and a median logging interval of 0.098 s. The results support agreement with the digital filter response and the provision of amplitude features for the data interface. Actual sampling accuracy, transmitter packet loss, and performance during active FES remain unevaluated.*

***Keywords:*** *electromyography, Butterworth digital filter, notch filter, STM32F411CEU6, hand rehabilitation*

# KATA PENGANTAR

Puji dan syukur penulis panjatkan ke hadirat Allah Subhanahu wa Ta'ala atas rahmat dan karunia-Nya sehingga Tugas Akhir berjudul “Rancang Bangun Tapis Digital Butterworth untuk Mengurangi Gangguan pada Sinyal Elektromiografi sebagai Masukan Sistem Rehabilitasi Tangan” dapat diselesaikan. Tugas Akhir ini disusun untuk memenuhi salah satu persyaratan memperoleh gelar Sarjana Teknik pada Program Studi Sarjana, Departemen Teknik Elektro, Fakultas Teknik, Universitas Diponegoro.

Penyusunan Tugas Akhir ini terlaksana dengan dukungan berbagai pihak. Oleh karena itu, penulis menyampaikan terima kasih kepada:

1. Bapak Ir. Aghus Sofwan, S.T., M.T., Ph.D., IPU selaku Ketua Departemen Teknik Elektro, Fakultas Teknik, Universitas Diponegoro atas dukungan kebijakan akademik, fasilitas, dan motivasi yang diberikan.
2. Bapak Achmad Hidayatno, S.T., M.T. dan Bapak Ir. Sumardi, S.T., M.T., IPM., ASEAN Eng. selaku dosen pembimbing yang senantiasa memberikan bimbingan, arahan, masukan ilmiah, evaluasi berharga, serta dukungan penuh selama perancangan subsistem hingga penyusunan laporan Tugas Akhir.
3. Bapak dan Ibu Dosen Penguji Sidang Tugas Akhir Departemen Teknik Elektro yang telah meluangkan waktu untuk menguji, mengevaluasi, serta memberikan kritik dan saran yang sangat membangun demi penyempurnaan karya ilmiah ini.
4. Aldin Zahwan dan Tsaqif Zain Khan Bhadrika sebagai rekan satu tim *capstone design* alat rehabilitasi tangan atas kerja sama yang solid, semangat kolaborasi, diskusi intensif, dan perjuangan bersama sepanjang penyelesaian proyek ini.
5. Orang tua dan segenap keluarga tercinta atas limpahan doa yang tiada henti, kasih sayang, kesabaran, pengorbanan, serta dukungan moral dan material yang menjadi kekuatan utama bagi penulis dalam menyelesaikan pendidikan sarjana.
6. Rekan-rekan mahasiswa Departemen Teknik Elektro, rekan-rekan laboratorium, serta seluruh pihak yang tidak dapat penulis sebutkan satu per satu yang telah memberikan bantuan teknis dan dukungan selama masa studi dan penelitian.

Penulis menyadari bahwa laporan ini masih memiliki keterbatasan. Kritik dan saran yang membangun diharapkan untuk perbaikan penelitian selanjutnya. Semoga Tugas Akhir ini dapat memberikan manfaat bagi pengembangan pemrosesan sinyal biomedis dan teknologi rehabilitasi.

Semarang, Agustus 2026

Penulis

# DAFTAR ISI

**HALAMAN JUDUL i**

[HALAMAN PERNYATAAN ORISINALITAS ii](#_Toc240344194)

[HALAMAN PERSETUJUAN iii](#_Toc240344195)

[HALAMAN PENGESAHAN iv](#_Toc240344196)

[HALAMAN PERNYATAAN PERSETUJUAN PUBLIKASI TUGAS AKHIR UNTUK KEPENTINGAN AKADEMIS v](#_Toc240344197)

[ABSTRAK vi](#_Toc240344198)

[ABSTRACT vii](#_Toc240344199)

[KATA PENGANTAR viii](#_Toc240344200)

[DAFTAR ISI x](#_Toc240344201)

[DAFTAR GAMBAR xiii](#_Toc240344202)

[DAFTAR TABEL xiv](#_Toc240344203)

[BAB I PENDAHULUAN 1](#_Toc240344204)

[1.1 Latar Belakang 1](#_Toc240344205)

[1.2 Rumusan Masalah 3](#_Toc240344206)

[1.3 Tujuan Penelitian 3](#_Toc240344207)

[1.4 Batasan Masalah 4](#_Toc240344208)

[1.5 Sistematika Penulisan 5](#_Toc240344209)

[BAB II KAJIAN PUSTAKA 6](#_Toc240344210)

[2.1 Penelitian Terdahulu 6](#_Toc240344211)

[2.2 *Stroke* dan Rehabilitasi Aktif pada Fungsi Tangan 9](#_Toc240344212)

[2.3 Sinyal Elektromiografi Permukaan 9](#_Toc240344213)

[2.4 Modul Sensor Elektromiografi DFRobot SEN0240 11](#_Toc240344214)

[2.5 Gangguan pada Sinyal Aktivitas Otot 13](#_Toc240344215)

[2.6 Pencuplikan Sinyal dan Pengubah Analog ke Digital 14](#_Toc240344216)

[2.7 Tapis Digital Butterworth 16](#_Toc240344217)

[2.8 Penekanan Gangguan Jala-Jala Listrik 50 Hz 19](#_Toc240344218)

[2.9 Nilai Aktivitas Otot 20](#_Toc240344219)

[BAB III PERANCANGAN SISTEM 22](#_Toc240344220)

[3.1 Analisis Kebutuhan Subsistem Pemrosesan Sinyal Aktivitas Otot 23](#_Toc240344221)

[3.2 Alat dan Bahan Subsistem Pemrosesan Sinyal EMG 25](#_Toc240344222)

[3.3 Perancangan Perangkat Keras dan Akuisisi Sinyal 27](#_Toc240344223)

[3.4 Perancangan *Filter* Digital Butterworth dan Takik 29](#_Toc240344224)

[3.4.1 Perancangan Butterworth Lolos Tinggi dan Lolos Rendah 29](#_Toc240344225)

[3.4.2 Perancangan Tapis Takik 50 Hz 33](#_Toc240344226)

[3.5 Perancangan Perangkat Lunak Pemrosesan Sinyal EMG 35](#_Toc240344227)

[3.5.1 Perancangan Kalibrasi dan Koreksi *Offset* 36](#_Toc240344228)

[3.5.2 Implementasi Kaskade Tapis Digital 37](#_Toc240344229)

[3.5.3 Perancangan Ekstraksi Fitur RMS dan MAV 38](#_Toc240344230)

[3.5.4 Perancangan Telemetri UART dan Pengolahan Data pada GUI 42](#_Toc240344231)

[3.6 Prosedur Pengujian dan Pengambilan Data 43](#_Toc240344232)

[BAB IV HASIL DAN PEMBAHASAN 49](#_Toc240344233)

[4.1 Hasil Implementasi dan Kondisi Pengujian 49](#_Toc240344234)

[4.2 Hasil Akuisisi dan Kualitas Data EMG 50](#_Toc240344235)

[4.3 Hasil Penapisan Digital Butterworth 52](#_Toc240344236)

[4.4 Hasil Tapis Takik 50 Hz 54](#_Toc240344237)

[4.5 Hasil Ekstraksi Fitur RMS dan MAV 57](#_Toc240344238)

[4.6 Analisis Aktivitas Otot pada Variasi Genggaman 58](#_Toc240344239)

[4.7 Analisis Konsistensi Aktivitas EMG pada Fase Perubahan Posisi Tangan 60](#_Toc240344240)

[4.8 Hasil Telemetri UART dan Pengolahan Data pada GUI 61](#_Toc240344241)

[4.9 Evaluasi Keseluruhan Subsistem Pemrosesan Sinyal EMG 63](#_Toc240344242)

[BAB V PENUTUP 65](#_Toc240344243)

[5.1 Kesimpulan 65](#_Toc240344244)

[5.2 Saran 66](#_Toc240344245)

[DAFTAR PUSTAKA 67](#_Toc240344246)

[BIODATA PENULIS 70](#_Toc240344247)

[LAMPIRAN A SENARAI PROGRAM STM32 71](#_Toc240344248)

[LAMPIRAN B DATA PENGUJIAN 73](#_Toc240344249)

# DAFTAR GAMBAR

Gambar 2.1 Pembentukan sinyal elektromiografi dari aktivitas unit motorik 10

Gambar 2.2 Modul sensor elektromiografi DFRobot SEN0240 12

Gambar 3.1 Integrasi keseluruhan sistem 22

Gambar 3.2 Diagram alir akuisisi, pemrosesan, telemetri, dan penyajian sinyal EMG 24

Gambar 3.3 Hubungan sensor DFRobot SEN0240 dengan ADC STM32F411CEU6 27

Gambar 3.4 Respons magnitudo teoretis koefisien rancangan HPF, LPF, dan takik 50 Hz 30

Gambar 3.5 Respons magnitudo tapis takik pada frekuensi 50 Hz 33

Gambar 3.6 Diagram alir implementasi pemrosesan sinyal EMG pada STM32F411CEU6 41

Gambar 4.1 Implementasi perangkat dan proses pengambilan data sinyal EMG 49

Gambar 4.2 Perubahan nilai MAV dan RMS hasil pemrosesan selama sesi pengujian 10 menit 52

Gambar 4.3 Perbandingan sinyal tanpa tapis digital dan setelah penapisan Butterworth pada kondisi genggaman kuat 53

Gambar 4.4 PSD sinyal sebelum dan sesudah tapis takik pada kondisi genggaman kuat 55

Gambar 4.5 PSD sinyal pada kondisi interferensi listrik 56

Gambar 4.6 Perbandingan nilai RMS pada variasi aktivitas otot 59

Gambar 4.7 Perbandingan rata-rata MAV dan RMS pada tiga jendela fase perubahan posisi tangan 61

Gambar 4.8 Perbandingan nilai RMS yang diterima dan hasil penghalusan EMA pada GUI 63

# DAFTAR TABEL

Tabel 2.1 Penelitian terdahulu yang berkaitan dengan pemrosesan sinyal aktivitas otot 8

Tabel 2.2 Karakteristik sinyal elektromiografi permukaan 11

Tabel 2.3 Spesifikasi modul sensor DFRobot SEN0240 13

Tabel 2.4 Gangguan pada sinyal aktivitas otot 14

Tabel 3.1 Pembagian kerja sistem alat rehabilitasi tangan 23

Tabel 3.2 Kebutuhan subsistem pemrosesan sinyal aktivitas otot 25

Tabel 3.3 Perangkat keras untuk akuisisi, pemrosesan, dan pengujian sinyal EMG 26

Tabel 3.4 Perangkat lunak yang digunakan 27

Tabel 3.5 Parameter akuisisi sinyal dan pembacaan ADC 28

Tabel 3.6 Parameter tapis digital Butterworth 31

Tabel 3.7 Normalisasi frekuensi batas tapis Butterworth 32

Tabel 3.8 Koefisien tapis Butterworth pada firmware 32

Tabel 3.9 Parameter perancangan tapis takik digital 34

Tabel 3.10 Koefisien tapis takik 50 Hz pada firmware 35

Tabel 3.11 Parameter kalibrasi dan koreksi offset 37

Tabel 3.12 Parameter ekstraksi fitur sinyal EMG 39

Tabel 3.13 Tahapan ekstraksi fitur sinyal EMG 40

Tabel 3.14 Tahapan telemetri UART dan pengolahan data pada GUI 43

Tabel 3.15 Titik pengambilan data pada pengujian subsistem EMG 44

Tabel 3.16 Kelompok rekaman raw untuk perbandingan usaha 46

Tabel 3.17 Hubungan tujuan penelitian, metode pengujian, dan tolok ukur 47

Tabel 4.1 Hasil pemeriksaan akuisisi dan kualitas data EMG 50

Tabel 4.2 Perbandingan nilai sebelum dan sesudah penapisan Butterworth 52

Tabel 4.3 Perbandingan respons teoritis dan eksperimen kaskade Butterworth 54

Tabel 4.4 Perbandingan nilai sebelum dan sesudah tapis takik 50 Hz 55

Tabel 4.5 Statistik nilai MAV dan RMS hasil akhir pemrosesan 57

Tabel 4.6 Nilai RMS pada variasi aktivitas otot 58

Tabel 4.7 Nilai MAV dan RMS pada fase perubahan posisi tangan 60

Tabel 4.8 Hasil pengujian telemetri UART dan penerimaan data pada GUI 61

Tabel 4.9 Ketercapaian tujuan penelitian berdasarkan hasil pengujian 63

# BAB I PENDAHULUAN

## Latar Belakang

Stroke dapat menyebabkan gangguan fungsi motorik yang membatasi kegiatan sehari-hari, termasuk menggenggam dan menggunakan tangan. World Health Organization (WHO) melaporkan beban stroke pada tahun 2021 sebesar sekitar 93,8 juta kasus prevalensi dan 11,9 juta kasus baru [1], [2]. Kebutuhan rehabilitasi fungsi tangan mendorong pengembangan perangkat yang dapat membantu latihan dan menerima informasi usaha aktif pengguna. Salah satu informasi biopotensial yang dapat digunakan ialah aktivitas listrik otot yang direkam melalui elektromiografi (EMG), khususnya elektromiografi permukaan atau *surface electromyography* (*sEMG*). Perekaman aktivitas otot menggunakan sinyal EMG memungkinkan pemberian stimulasi listrik dilakukan secara adaptif ketika pengguna berupaya menggerakkan tangan, bukan secara terus-menerus [3], [4]. Dalam konteks tersebut, kualitas sinyal masukan perlu diperhatikan agar perubahan aktivitas otot tidak tertukar dengan perubahan akibat gangguan perekaman.

Penelitian terdahulu menunjukkan beberapa pendekatan untuk menghubungkan usaha pengguna dengan bantuan stimulasi listrik fungsional atau *Functional Electrical Stimulation* (FES). Muhammad A. Khan, H. Fares, H. Ghayvat, I. C. Brunner, S. Puthusserypady, B. Razavi, M. Lansberg, A. Poon, dan K. J. Meador [3] menelaah 25 studi yang mencakup FES terbuka, FES berbasis antarmuka otak-komputer, dan FES berbasis EMG. Kajian tersebut melaporkan perbaikan fungsi anggota gerak atas pada kelompok yang dianalisis. F. Rossi, P. Motto Ros, R. M. Rosales, dan D. Demarchi [4] mengembangkan sistem FES tertanam yang menggunakan fitur *Average Threshold Crossing* (ATC) dari *sEMG* dan mengujinya pada 11 subjek sehat. Penelitian tersebut menunjukkan kelayakan pemrosesan *sEMG* tertanam sebagai bagian jalur masukan sistem stimulasi.

Pada jalur masukan tersebut, elektroda dan rangkaian pengondisi menyediakan sinyal analog, sedangkan pemrosesan digital membatasi kandungan frekuensi dan membentuk fitur amplitudo. K. Li, J. Zhang, L. Wang, M. Zhang, J. Li, dan S. Bao [5] membahas prapemrosesan serta pengenalan intensi pada sistem interaksi manusia-robot berbasis *sEMG*. F. Mandrile, D. Farina, M. Pozzo, dan R. Merletti [6] menunjukkan bahwa stimulasi listrik dapat menimbulkan artefak pada rekaman *sEMG*. T. Roland, S. Amsuess, M. F. Russold, dan W. Baumgartner [7] menerapkan penapisan digital pada sensor EMG kapasitif dengan mempertimbangkan penekanan gangguan dan daya sinyal yang dipertahankan. Ketiga kajian tersebut menempatkan kualitas perekaman dan pemilihan tapis sebagai persoalan tersendiri yang perlu dinilai sebelum keluaran sinyal digunakan oleh subsistem berikutnya.

Pilihan tapis digital mencakup Finite Impulse Response (FIR) dan Infinite Impulse Response (IIR). FIR dapat dirancang dengan fase linear, sedangkan IIR umumnya memerlukan orde lebih rendah untuk ketajaman transisi yang sebanding. Butterworth dipilih karena respons magnitudonya tanpa riak pada pita lolos ideal dan dapat direalisasikan dengan bagian orde dua [8], [9]. Karakter ini sesuai dengan pengamatan fitur amplitudo. Komponen sekitar 50 Hz berada di dalam pita sEMG sehingga memerlukan tahap takik tersendiri [10]. Dasar rancangan tersebut selanjutnya diperiksa melalui respons koefisien dan pasangan rekaman sebelum serta sesudah tapis.

Tugas akhir ini mengimplementasikan dan mengevaluasi jalur pemrosesan sEMG pada STM32F411CEU6, mulai dari keluaran SEN0240 hingga fitur RMS dan MAV. Persoalan yang dinilai ialah kesesuaian pembatasan pita digital, pelemahan komponen sekitar 50 Hz, serta penyediaan fitur untuk antarmuka sistem capstone. Kontribusi individu mencakup konfigurasi akuisisi, realisasi kaskade, ekstraksi fitur, dan evaluasi menggunakan data antartahap. Nilai kontribusinya terletak pada penerapan serta pembuktian karakteristik subsistem tersebut. Pengujian tanpa stimulasi aktif memberi dasar bagi integrasi lanjutan sesuai batas pada Subbab 1.4.

Dalam judul, pengurangan gangguan dievaluasi melalui pembatasan pita dan pelemahan spektral yang teramati. Keluaran sebagai masukan rehabilitasi dinilai pada penyediaan fitur dan antarmuka data. Hasil tidak dipakai untuk menyatakan manfaat terapi atau ketahanan terhadap artefak stimulasi, karena kedua aspek memerlukan pengujian sistem terpadu.

## Rumusan Masalah

Berdasarkan latar belakang yang telah diuraikan, rumusan masalah dalam penelitian ini adalah sebagai berikut:

1. Bagaimana merancang dan mengimplementasikan kaskade Butterworth lolos tinggi 20 Hz, lolos rendah 500 Hz, serta tapis takik 50 Hz pada STM32F411CEU6?
2. Bagaimana kesesuaian respons Butterworth dengan koefisien rancangan serta besarnya pelemahan komponen sekitar frekuensi sasaran oleh tapis takik pada data pengujian?
3. Bagaimana karakteristik fitur RMS dan MAV pada sesi pengujian dan variasi usaha genggaman, serta konsistensi nilai RMS yang diterima GUI melalui UART?

## Tujuan Penelitian

Penelitian tugas akhir ini bertujuan untuk:

1. Merancang dan mengimplementasikan tapis digital Butterworth berupa kaskade lolos-tinggi 20 Hz dan lolos-rendah 500 Hz pada STM32F411CEU6, disertai tapis takik 50 Hz, untuk menyediakan sinyal EMG terproses sebagai masukan sistem rehabilitasi tangan.
2. Mengevaluasi respons Butterworth terhadap koefisien rancangan dan mengukur pelemahan komponen sekitar frekuensi sasaran takik melalui perbandingan sinyal sebelum serta sesudah tahap digital.
3. Mengevaluasi karakteristik RMS dan MAV pada sesi pengujian dan variasi usaha genggaman, serta konsistensi isi dan interval pencatatan nilai RMS yang diterima GUI melalui UART.

## Batasan Masalah

1. Penelitian berfokus pada subsistem akuisisi dan pemrosesan elektromiografi permukaan sebagai penyedia masukan sistem rehabilitasi tangan. Kesiapan kendali dan hasil terapi sistem secara keseluruhan tidak menjadi keluaran evaluasi.
2. Sinyal diperoleh dari keluaran analog SEN0240 yang telah melalui pengondisian internal sensor. Evaluasi respons frekuensi membandingkan titik sebelum dan sesudah tapis digital, sehingga ruang lingkupnya mencakup tahap digital setelah ADC.
3. Mikrokontroler STM32F411CEU6 digunakan untuk membaca sinyal analog melalui pengubah analog ke digital atau *Analog-to-Digital Converter* (ADC), menerapkan algoritma tapis digital, dan menghitung fitur aktivitas otot.
4. Evaluasi penapisan mencakup respons magnitudo Butterworth dan pelemahan spektral oleh takik. Perubahan RMS dan MAV menyatakan perubahan fitur amplitudo. Penelitian tidak mengukur rasio sinyal terhadap derau menggunakan acuan fisiologis yang terpisah.
5. Penelitian ini tidak membahas perancangan *stimulator* listrik, algoritma kendali utama, antarmuka pengguna, pengujian klinis pada pasien *stroke*, maupun perancangan rangkaian internal modul sensor.
6. Pengujian karakteristik tapis digital dilakukan tanpa stimulasi listrik aktif, sehingga penelitian ini tidak mengevaluasi kemampuan tapis dalam meredam artefak yang muncul selama stimulasi listrik berlangsung.
7. Pengujian menggunakan satu subjek, yaitu penulis, pada lengan bawah kiri. Pengulangan merepresentasikan variasi dalam sesi pengujian dan tidak mewakili keragaman populasi atau kondisi pasien *stroke*.

## Sistematika Penulisan

Sistematika penulisan laporan tugas akhir ini disusun sebagai berikut.

**BAB I PENDAHULUAN**

Bab ini menjelaskan latar belakang, rumusan masalah, tujuan, batasan penelitian, dan susunan laporan.

**BAB II KAJIAN PUSTAKA**

Bab ini merangkum penelitian terdahulu dan teori tentang rehabilitasi tangan, EMG, gangguan sinyal, pencuplikan, penapisan, dan perhitungan aktivitas otot.

**BAB III PERANCANGAN SISTEM**

Bab ini menjelaskan kebutuhan subsistem, perangkat keras dan akuisisi, perancangan *filter* digital, implementasi perangkat lunak, serta prosedur dan tolok ukur pengujian.

**BAB IV HASIL DAN PEMBAHASAN**

Bab ini menyajikan hasil pengujian tapis, perubahan nilai aktivitas otot, dan penerimaan hasil pemrosesan melalui UART pada GUI.

**BAB V PENUTUP**

Bab ini memuat kesimpulan dan saran pengembangan.

# BAB II KAJIAN PUSTAKA

## Penelitian Terdahulu

Muhammad A. Khan, H. Fares, H. Ghayvat, I. C. Brunner, S. Puthusserypady, B. Razavi, M. Lansberg, A. Poon, dan K. J. Meador [3] pada tahun 2023 melakukan telaah sistematis dan meta-analisis sistem rehabilitasi anggota gerak atas pascastroke berbasis FES. Mereka mengelompokkan 25 studi menjadi delapan studi FES terbuka, 13 studi FES berbasis antarmuka otak-komputer, dan empat studi FES berbasis EMG. Evaluasi menggunakan ukuran fungsi motorik baku, termasuk *Fugl-Meyer Assessment* dan *Action Research Arm Test*. Hasil analisis menunjukkan perbaikan fungsi motorik pada kelompok yang ditelaah. Temuan tersebut mendukung perancangan sistem FES yang melibatkan usaha volunter pengguna.

F. Rossi, P. Motto Ros, R. M. Rosales, dan D. Demarchi [4] pada tahun 2020 mengembangkan sistem FES tertanam yang dikendalikan oleh sEMG berbasis kejadian. Mereka menggunakan fitur Average Threshold Crossing (ATC), mengevaluasi efisiensi komputasi sistem, dan melakukan pengujian gerak pada 11 subjek sehat. Korelasi antara profil gerak sukarela dan gerak hasil stimulasi mencapai 0,87 ± 0,07 pada fleksi siku dan 0,93 ± 0,02 pada ekstensi lutut. Hasil tersebut menunjukkan kelayakan pengolahan sEMG tertanam sebagai jalur masukan stimulasi pada kondisi yang diuji.

K. Li, J. Zhang, L. Wang, M. Zhang, J. Li, dan S. Bao [5] pada tahun 2020 menelaah teknologi utama sistem interaksi manusia-robot berbasis *sEMG*. Kajian tersebut membahas tahapan prapemrosesan sinyal, ekstraksi fitur domain waktu dan frekuensi, pengenalan intensi gerak, serta ketahanan pengenalan terhadap derau. Hasil kajian menegaskan bahwa mutu sinyal biopotensial dan keandalan metode penapisan merupakan faktor kunci penentu keberhasilan sistem interaksi berbasis EMG.

F. Mandrile, D. Farina, M. Pozzo, dan R. Merletti [6] pada tahun 2003 meneliti pengaruh bentuk pulsa, konfigurasi sistem deteksi, amplitudo arus, dan penempatan elektroda terhadap artefak stimulasi pada rekaman sEMG. Mereka melakukan pengujian stimulasi pada otot biseps dengan tujuh variasi bentuk gelombang serta larik delapan elektroda. Temuan mereka menunjukkan bahwa jarak elektroda perekam terhadap lokasi elektroda stimulasi sangat menentukan besar artefak yang terinduksi, sehingga konfigurasi perekaman perlu dinilai bersama metode penanganan artefak.

T. Roland, S. Amsuess, M. F. Russold, dan W. Baumgartner [7] pada tahun 2019 mengembangkan arsitektur penapisan digital berdaya rendah untuk sensor EMG kapasitif. Mereka merancang dan membandingkan kinerja tapis untuk menekan interferensi jala-jala listrik dan artefak gerak frekuensi rendah, kemudian mengimplementasikannya menggunakan aritmetika titik tetap pada mikrokontroler. Hasil penelitian menunjukkan adanya kompromi teknis antara derajat penekanan derau, integritas daya EMG yang dipertahankan, dan kompleksitas beban komputasi prosesor. Tabel 2.1 menyajikan rangkuman perbandingan kelima penelitian terdahulu tersebut.

Tabel 2.1 Penelitian terdahulu yang berkaitan dengan pemrosesan sinyal aktivitas otot.

| **Peneliti** | **Fokus penelitian** | **Metode** | **Hasil utama** |
| --- | --- | --- | --- |
| M. A. Khan [3] | Rehabilitasi anggota gerak atas dengan FES | Telaah 25 studi: 8 terbuka, 13 BCI, 4 EMG | Perbaikan fungsi pada kelompok yang dianalisis, dengan batas perbandingan antarprotokol |
| F. Rossi [4] | FES tertanam berbasis *sEMG* | *Average Threshold Crossing* dan uji 11 subjek sehat | Korelasi gerak 0,87 pada siku dan 0,93 pada lutut |
| K. Li [5] | Interaksi manusia-robot berbasis *sEMG* | Telaah pemrosesan, pengenalan intensi, dan fusi informasi | Mutu sinyal dan ketahanan pengenalan menjadi tantangan utama |
| F. Mandrile [6] | Artefak stimulasi pada *sEMG* | Variasi bentuk pulsa, arus, posisi, dan deteksi elektroda | Jarak dari lokasi stimulasi memengaruhi artefak ternormalisasi |
| T. Roland [7] | Penapisan EMG kapasitif berdaya rendah | Tapis sisir dan lolos tinggi dengan titik tetap | Ada kompromi penekanan gangguan, daya EMG, dan komputasi |

Kajian tersebut menghubungkan pemanfaatan sEMG dengan mutu perekaman, ekstraksi fitur, dan penapisan digital. Hasil klinis pada sistem FES serta hasil sensor kapasitif berlaku pada perangkat dan kondisi pengujian masing-masing. Temuan tersebut menjadi dasar teori, sedangkan kesesuaian koefisien dan perubahan sinyal pada suatu implementasi tetap memerlukan evaluasi tersendiri. Tapis berbasis frekuensi juga dapat melemahkan komponen fisiologis yang berada pada frekuensi yang sama dengan gangguan.

## *Stroke* dan Rehabilitasi Aktif pada Fungsi Tangan

Stroke terjadi akibat gangguan aliran darah menuju jaringan otak karena sumbatan pembuluh darah maupun perdarahan vaskular serebral. Dampaknya bergantung pada lokasi lesi otak dan luas jaringan yang mengalami iskemia. Penurunan kemampuan fungsi motorik dapat mencakup kelemahan otot pada satu sisi tubuh (hemiparesis), kesulitan mengendalikan koordinasi gerak, serta hilangnya kemampuan fungsional tangan dalam menggenggam benda. Kondisi tersebut menurunkan kemandirian pasien dalam menjalani aktivitas hidup sehari-hari sehingga membutuhkan intervensi rehabilitasi yang intensif [1], [2].

Rehabilitasi aktif melibatkan usaha gerak volunter pengguna selama latihan. FES memberikan pulsa listrik untuk memicu kontraksi otot. Sistem berbasis sEMG dapat memakai ambang aktivitas sebagai pemicu atau memakai besarnya fitur untuk mengatur bantuan, sesuai rancangan kendali [3], [4]. Kajian Khan dkk. [3] melaporkan hasil pemulihan pada studi pascastroke, sedangkan Rossi dkk. [4] menguji kelayakan perangkat pada subjek sehat. Kedua jenis bukti tersebut memiliki lingkup penilaian yang berbeda.

Pemanfaatan *sEMG* memerlukan perhatian terhadap mutu perekaman. Posisi elektroda, kondisi kontak kulit, gerakan kabel, dan interferensi lingkungan dapat mengubah sinyal yang diperoleh. Jika stimulasi listrik berlangsung bersamaan, artefak stimulasi juga dapat masuk ke jalur perekaman [6], [10]. Oleh karena itu, keluaran fitur amplitudo perlu ditafsirkan bersama kondisi pengukuran. Penapisan frekuensi saja tidak menjamin bahwa seluruh komponen gangguan dapat dipisahkan dari aktivitas otot.

## Sinyal Elektromiografi Permukaan

Sinyal sEMG merekam perubahan potensial listrik yang timbul ketika unit motorik mengaktifkan serat-serat otot skelet. Elektroda diletakkan di atas permukaan kulit sehingga perekaman tidak memerlukan elektroda yang menembus kulit. Karena bentuk gelombang biopotensial dipengaruhi oleh konduktivitas jaringan subkutan dan orientasi serat otot, prosedur perekaman memerlukan konsistensi penempatan dan jarak elektroda [12]. Sinyal yang teramati merupakan superposisi dari banyak potensial aksi unit motorik, sebagaimana diperlihatkan pada Gambar 2.1 [11].

![Pictorial outline of the decomposition of the surface EMG signal into its constituent motor unit action potentials. (Adapted from De Luca et al. 1982a.)  ](data:image/png;base64...)

Gambar 2.1 Pembentukan sinyal elektromiografi dari aktivitas unit motorik

Amplitudo *sEMG* umumnya meningkat ketika lebih banyak unit motorik direkrut atau laju tembaknya bertambah. Walaupun demikian, hubungan amplitudo *sEMG* dengan gaya tidak selalu linear karena dipengaruhi panjang otot, jenis kontraksi, kelelahan, jaringan di bawah kulit, serta kualitas kontak elektroda [13]. Oleh sebab itu, RMS atau MAV lebih tepat dipakai untuk membandingkan tingkat aktivitas secara relatif pada kondisi pengukuran yang terjaga daripada sebagai pengukur gaya absolut. Karakteristik penting *sEMG* dirangkum pada Tabel 2.2.

Tabel 2.2 Karakteristik sinyal elektromiografi permukaan.

| **Parameter** | **Karakteristik** | **Makna teoretis** |
| --- | --- | --- |
| Amplitudo | Kecil dan dipengaruhi kondisi perekaman | Memerlukan pengondisian dan pemrosesan yang stabil |
| Spektrum utama | Sekitar 20–500 Hz | Menjadi acuan umum pembatasan pita *sEMG* |
| Komponen frekuensi rendah | Dominan di bawah sekitar 20 Hz | Dapat berkaitan dengan artefak gerakan dan perubahan kontak elektroda |
| Jala-jala listrik | 50 Hz pada sistem tenaga Indonesia | Berada di dalam pita *sEMG* sehingga memerlukan penanganan selektif |
| Komponen frekuensi tinggi | Di atas pita utama *sEMG* | Dapat dibatasi dengan tapis lolos-rendah tanpa menafsirkan semua komponennya sebagai derau |

Sebagian besar daya *sEMG* berada pada rentang puluhan hingga ratusan hertz. Literatur pemrosesan EMG sering menggunakan rentang praktis sekitar 20–500 Hz, sedangkan komponen sangat rendah dapat didominasi artefak gerakan dan perubahan kontak elektroda [7], [10]. Komponen jala-jala 50 Hz berada di dalam rentang tersebut, sehingga pembatasan pita saja tidak cukup untuk memisahkannya.

## Modul Sensor Elektromiografi DFRobot SEN0240

DFRobot SEN0240 merupakan modul *sEMG* noninvasif yang menggunakan elektroda kering serta rangkaian penguatan dan penapisan terintegrasi. Dokumentasi produsen menyatakan bahwa modul bekerja pada catu 3,3–5,5 V, menggunakan titik referensi keluaran sekitar 1,5 V, dan menghasilkan tegangan analog sekitar 0–3,0 V. Spektrum efektif keluarannya berada pada kisaran 20–500 Hz [14]. Dengan demikian, keluaran modul bukan potensial elektroda mentah, melainkan sinyal analog yang telah mengalami pengondisian awal.

![](data:image/png;base64...)

Gambar 2.2 Modul sensor elektromiografi DFRobot SEN0240

Modul pada Gambar 2.2 menyediakan keluaran analog untuk dibaca ADC. Kesesuaian rentang tegangan mengacu pada dokumentasi produsen, bukan pada tampilan fisik modul. Produsen merekomendasikan resolusi ADC lebih dari 8 bit dan frekuensi pencuplikan sedikitnya 1 kHz [14]. ADC STM32F411xC/xE memiliki resolusi 12 bit, beberapa kanal masukan, dan dukungan pemicu *timer* [15]. Rincian tegangan kerja, rentang keluaran, dan pengondisian internal tercantum pada Tabel 2.3.

Tabel 2.3 Spesifikasi modul sensor DFRobot SEN0240.

| **Parameter** | **Keterangan** |
| --- | --- |
| Jenis sensor | Sensor elektromiografi permukaan |
| Elektroda | Elektroda kering |
| Tegangan kerja | 3,3 sampai 5,5 V |
| Keluaran | Tegangan analog |
| Rentang keluaran | Sekitar 0 sampai 3 V |
| Fungsi keluaran | Menyediakan sinyal analog terkondisi untuk dibaca ADC |
| Pengondisian internal | Penguatan, masukan diferensial, dan penapisan analog terintegrasi |
| Rentang spektrum efektif | Sekitar 20–500 Hz |

## Gangguan pada Sinyal Aktivitas Otot

Sinyal *sEMG* memiliki amplitudo relatif kecil sehingga mudah dipengaruhi gangguan fisiologis, mekanis, dan elektromagnetik. Pergeseran elektroda, gerakan kabel, perubahan impedansi kontak kulit, serta gerakan jaringan dapat menimbulkan artefak yang dominan pada frekuensi rendah. Gangguan berfrekuensi lebih tinggi dapat berasal dari rangkaian elektronik dan lingkungan. McManus dkk. [10] menekankan bahwa jenis serta besar gangguan dipengaruhi sistem elektroda, pemasangan, dan kondisi perekaman, sehingga satu batas frekuensi tidak dapat dianggap menghilangkan semua artefak.

Interferensi jala-jala muncul di sekitar frekuensi sistem tenaga, yaitu 50 Hz di Indonesia, dan dapat masuk melalui kopling kapasitif dari kabel, adaptor, komputer, atau tubuh pengguna. Pada sistem yang menggabungkan *sEMG* dan FES, pulsa stimulasi juga dapat menghasilkan artefak beramplitudo besar pada rekaman. Mandrile dkk. [6] menunjukkan bahwa jarak elektroda perekam dari titik stimulasi berpengaruh terhadap artefak ternormalisasi, sedangkan Roland dkk. [7] menunjukkan perlunya kompromi antara penekanan gangguan dan pemeliharaan daya *sEMG*. Tabel 2.4 mengaitkan sumber gangguan dengan perubahan yang dapat muncul pada rekaman.

Tabel 2.4 Gangguan pada sinyal aktivitas otot.

| **Jenis Gangguan** | **Penyebab** | **Pengaruh terhadap Sinyal** |
| --- | --- | --- |
| Artefak gerakan | Pergeseran elektroda, gerakan kabel, atau perubahan kontak kulit | Menyebabkan pergeseran garis dasar sinyal |
| Gangguan jala-jala listrik 50 Hz | Sumber listrik dan peralatan elektronik di sekitar alat | Menimbulkan komponen 50 Hz pada sinyal |
| Gangguan frekuensi tinggi | Rangkaian elektronik dan interferensi elektromagnetik | Membuat sinyal lebih berisik dan tidak stabil |
| Artefak stimulasi listrik | Pulsa stimulasi dari sistem rehabilitasi | Dapat terbaca sebagai aktivitas otot palsu |

## Pencuplikan Sinyal dan Pengubah Analog ke Digital

Pencuplikan mengubah sinyal analog kontinu menjadi deret nilai pada waktu diskrit. Menurut teorema Nyquist-Shannon, frekuensi pencuplikan harus lebih besar daripada dua kali frekuensi tertinggi yang ingin direpresentasikan agar pelipatan spektrum atau *aliasing* dapat dihindari secara ideal [8], [9]. Dalam praktik, diperlukan jarak transisi bagi penapis analog *anti-alias* sebelum ADC karena komponen di atas frekuensi Nyquist tidak dapat dihilangkan kembali hanya dengan tapis digital setelah pencuplikan.

ADC mengubah setiap tegangan hasil pencuplikan menjadi kode digital dengan jumlah tingkat yang ditentukan oleh resolusinya. ADC 12 bit memiliki 4.096 tingkat kuantisasi, sedangkan ketelitian tegangan aktual juga dipengaruhi tegangan referensi, derau, waktu pencuplikan, dan karakteristik masukan. *Datasheet* STM32F411xC/xE menjelaskan bahwa perangkat ini memiliki ADC 12 bit yang dapat dipicu oleh *timer* dan dilayani DMA [15]. Hubungan sensor, rentang masukan, resolusi, laju pencuplikan, serta tapis *anti-alias* perlu dianalisis bersama pada tahap perancangan, bukan dianggap sebagai satu parameter yang berdiri sendiri.

Pada pemetaan ujung rentang ADC, kode nol dipetakan ke nol volt dan kode maksimum ke tegangan referensi. Skala konversi dan tegangan setiap sampel mengikuti Persamaan 2.1 dan 2.2. Simbol N menyatakan resolusi dalam bit, VREF tegangan referensi, dan ADC[n] kode pada sampel ke-n. Skala pemetaan VREF/(2ᴺ − 1) berbeda dari lebar kuantisasi ideal VREF/2ᴺ [8], [15].

|  | (2.1) |
| --- | --- |
|  | (2.2) |

Sinyal *bipolar* dapat memiliki komponen tetap atau *offset* akibat titik kerja rangkaian. Rata-rata M sampel pada kondisi acuan memperkirakan *offset*. Pengurangan *offset* menghasilkan sinyal berpusat di sekitar nol. Persamaan 2.3 dan 2.4 menyatakan kedua proses tersebut. Nilai xADC[k] merupakan kode ADC ke-k, xoffset rata-rata kalibrasi, dan xkoreksi[n] selisih kode setelah koreksi.

|  | (2.3) |
| --- | --- |
|  | (2.4) |

Koreksi *offset* mengurangi komponen tetap pada kondisi acuan. Koreksi ini tidak menggantikan penapis frekuensi atau menjamin hilangnya perubahan garis dasar setelah kondisi perekaman berubah. Untuk menyatakan sinyal terkoreksi dalam volt, selisih kode dikalikan dengan skala pada Persamaan 2.1.

## Tapis Digital Butterworth

Respons magnitudo Butterworth bersifat maksimal-datar pada pita lolos ideal tanpa riak. Transisinya menuju pita redam berlangsung bertahap. Karakteristik prototipe analog lolos rendah berorde r dinyatakan melalui kuadrat magnitudo pada Persamaan 2.5. Dalam hubungan ini, Ω menyatakan frekuensi sudut analog dan Ωc frekuensi batas [8], [16].

|  | (2.5) |
| --- | --- |

Pada Ω = Ωc, magnitudo bernilai 1/√2 dari penguatan pita lolos, setara dengan −3,0103 dB. Setiap penambahan orde memperbesar kemiringan asimtotik sebesar 20 dB per dekade. Butterworth tidak memiliki fase linear secara umum. Pemilihan orde juga mempertimbangkan perubahan fase dan kebutuhan komputasi [8], [20].

Prototipe Butterworth orde dua memiliki penyebut terstandar s² + √2s + 1. Fungsi alih lolos rendah dan lolos tinggi menggunakan penyebut yang sama, dengan pembilang berbeda seperti pada Persamaan 2.6. Variabel s merupakan variabel kompleks transformasi Laplace.

|  | (2.6) |
| --- | --- |

Agar frekuensi batas dapat digunakan dalam rancangan diskrit, fc dinormalisasi terhadap frekuensi Nyquist fs/2 melalui Persamaan 2.7. Hasilnya berada di antara nol dan satu untuk frekuensi di bawah Nyquist. Simbol fs menyatakan frekuensi pencuplikan [20].

|  | (2.7) |
| --- | --- |

Transformasi bilinear pada Persamaan 2.8 menghubungkan prototipe analog dengan bidang z. Karena pemetaan frekuensinya tidak linear, *prewarping* menyesuaikan frekuensi batas analog agar batas digital tetap berada pada nilai yang dituju [8], [9].

|  | (2.8) |
| --- | --- |

Satu bagian orde dua atau *biquad* memiliki fungsi alih pada Persamaan 2.9 dengan a0 dinormalisasi menjadi satu. Koefisien b0, b1, b2 membentuk pembilang, sedangkan a1 dan a2 membentuk penyebut. Faktor z⁻¹ menyatakan penundaan satu sampel. Hubungan masukan dan keluaran dalam domain waktu mengikuti Persamaan 2.10 [8], [22].

|  | (2.9) |
| --- | --- |
|  | (2.10) |

Pada Persamaan 2.10, x[n] dan y[n] menyatakan masukan dan keluaran pada indeks n. Simbol bk dan ak menyatakan koefisien, sedangkan M dan N menyatakan orde pembilang dan penyebut. Nilai M = N = 2 menghasilkan satu *biquad*. Sistem IIR kausal stabil jika seluruh *pole* berada di dalam lingkaran satuan. Fungsi alih kaskade merupakan perkalian fungsi alih tiap bagian.

Koefisien Butterworth orde dua dapat dihitung dari K = tan(πfc/fs) dan D = 1 + √2K + K². Substitusi prototipe analog ke transformasi bilinear menghasilkan koefisien lolos rendah pada Persamaan 2.11 dan lolos tinggi pada Persamaan 2.12. Kedua jenis menggunakan a1 = 2(K² − 1)/D dan a2 = (1 − √2K + K²)/D.

|  | (2.11) |
| --- | --- |
|  | (2.12) |

Realisasi *Direct Form II Transposed* menyimpan dua variabel keadaan untuk setiap *biquad*. Struktur ini merealisasikan hubungan pada Persamaan 2.10 tanpa menyimpan seluruh riwayat sampel. Koefisien dan keadaan internal menentukan respons setiap bagian, sehingga *reset* keadaan dapat memengaruhi transien keluaran [8].

Pada sistem linear dengan keadaan awal nol, urutan bagian tidak mengubah fungsi alih total. Urutan tetap perlu dinyatakan karena memengaruhi sinyal antara dan perhitungan numerik [8].

Evaluasi respons dapat menggunakan pasangan masukan x dan keluaran y yang direkam sinkron. Estimator H1 pada Persamaan 2.13 menggunakan spektrum silang Sxy dan spektrum daya masukan Sxx. Magnitudonya dinyatakan dalam desibel melalui Persamaan 2.14 [18].

|  | (2.13) |
| --- | --- |
|  | (2.14) |

Estimator tersebut memerlukan energi masukan yang cukup pada frekuensi yang dinilai. Respons eksperimen dibandingkan dengan respons teoritis dari koefisien. Selisih keduanya menilai kesesuaian implementasi, sedangkan perubahan amplitudo total saja tidak menunjukkan bagian spektrum yang mengalami pelemahan.

## Penekanan Gangguan Jala-Jala Listrik 50 Hz

Tapis takik atau *notch filter* menolak pita sempit di sekitar frekuensi tengah f0. Frekuensi 50 Hz masih berada dalam pita *sEMG* sehingga tapis lolos-tinggi dan lolos rendah tidak cukup untuk menekan komponen jala-jala secara selektif. Takik mengurangi komponen di sekitar sasaran sambil mempertahankan sebagian besar frekuensi lainnya [7], [10].

Lebar penolakan takik bergantung pada frekuensi tengah dan faktor kualitasnya. Persamaan 2.15 mengubah f0 menjadi frekuensi sudut ω0 dalam radian per sampel. Sementara itu, Persamaan 2.16 mengaitkan faktor kualitas Q dengan lebar pita penolakan BW pada batas −3 dB [21].

|  | (2.15) |
| --- | --- |
|  | (2.16) |

Salah satu formulasi takik IIR orde dua menggunakan parameter β dan g pada Persamaan 2.17. Dengan a0 = 1, koefisien pada Persamaan 2.18 membentuk fungsi alih *biquad* seperti Persamaan 2.9. Formulasi ini memakai lebar pita dalam radian per sampel dan menempatkan pasangan *zero* pada frekuensi sasaran [21].

|  | (2.17) |
| --- | --- |
|  | (2.18) |

Q yang besar menghasilkan takik sempit. Selektivitas tersebut mengurangi perubahan komponen di luar sasaran, tetapi pelemahannya turun ketika frekuensi gangguan bergeser. Satu takik tidak otomatis menekan harmonik frekuensi jala-jala. Respons, kestabilan *pole*, dan pergeseran interferensi perlu diperiksa bersama [7], [21].

Pelemahan komponen dapat dinilai dari rasio *power spectral density* (PSD) sebelum dan sesudah tapis. Metode Welch mengestimasi PSD melalui pembagian data menjadi segmen berjendela dan perataan periodogram termodifikasi [19]. Persamaan 2.19 menyatakan pelemahan A(f) dalam desibel. Psebelum dan Psetelah harus memakai metode, satuan, dan pengaturan spektrum yang sama.

|  | (2.19) |
| --- | --- |

Nilai A(f) positif menunjukkan bahwa daya pada frekuensi tersebut menurun. Nilai mendekati nol menunjukkan perubahan kecil. Pelemahan spektral di sekitar gangguan berbeda dari penurunan RMS seluruh sinyal karena RMS juga memuat komponen aktivitas otot pada frekuensi lain.

## Nilai Aktivitas Otot

Sampel *sEMG* *bipolar* dapat diringkas menjadi fitur amplitudo dalam jendela pengamatan. Banyaknya sampel ditentukan oleh durasi jendela Tw dan laju pencuplikan fs melalui Persamaan 2.20. Dengan Tw dalam detik, hasil N harus berupa bilangan bulat. Jendela tanpa *overlap* menghasilkan satu pembaruan setiap Tw, sedangkan jendela bertumpang tindih memperbarui fitur sesuai besar pergeserannya [5], [10].

|  | (2.20) |
| --- | --- |

Fitur RMS menyatakan nilai efektif sinyal melalui Persamaan 2.21. Perhitungannya mengkuadratkan setiap sampel, merata-ratakannya dalam satu jendela data, lalu menarik akar kuadrat dari rata-rata tersebut. Pembobotan kuadrat membuat fitur ini sensitif terhadap peningkatan amplitudo yang dihasilkan saat lebih banyak unit motorik direkrut atau frekuensi tembaknya meningkat.

|  | (2.21) |
| --- | --- |

Berbeda dari pembobotan kuadrat pada RMS, fitur MAV merata-ratakan nilai mutlak sampel dalam satu jendela waktu melalui Persamaan 2.22. Sifat linearnya menghasilkan komputasi yang efisien pada mikrokontroler serta respons yang proporsional terhadap amplitudo sinyal.

|  | (2.22) |
| --- | --- |

Panjang jendela menentukan interval pembaruan fitur dan tingkat perataan. Jendela tanpa overlap menghasilkan satu nilai setelah N sampel terkumpul. Jitter pencuplikan ialah perubahan selang waktu antarsampel terhadap periode nominal pencuplikan. Latensi ujung ke ujung ialah waktu dari perubahan sinyal pada masukan sensor sampai hasilnya tersedia di GUI. Keduanya memerlukan acuan waktu yang terukur. Durasi jendela dan interval log GUI tidak dapat menggantikan pengukuran itu.

RMS dan MAV menyatakan amplitudo pada kondisi perekaman tertentu. Lokasi elektroda, kontak kulit, penguatan, dan jenis kontraksi memengaruhi nilainya. Perbandingan memerlukan kondisi yang terjaga dan tidak langsung mengukur gaya atau kemampuan klinis [10], [13].

# BAB III PERANCANGAN SISTEM

*Capstone design* ini berupa alat rehabilitasi tangan yang menggabungkan pembacaan aktivitas otot, pengambilan keputusan pada antarmuka, dan stimulasi listrik fungsional. Sensor *sEMG* membaca aktivitas otot lengan bawah dan menghasilkan sinyal analog. Sinyal tersebut masuk ke ADC mikrokontroler untuk diubah menjadi data digital dan diproses menjadi nilai aktivitas otot. Nilai hasil pemrosesan dikirim ke GUI, kemudian subsistem kendali menggunakan informasi tersebut bersama parameter terapi untuk menentukan perintah yang diteruskan ke subsistem stimulator. Integrasi keseluruhan sistem disediakan dalam Gambar 3.1.

![](data:image/png;base64...)

Gambar 3.1 Integrasi keseluruhan sistem.

Pada Gambar 3.1, penyelesaian sistem dibagi menjadi tiga bagian yang saling berhubungan. Aldin Zahwan menyelesaikan perancangan subsistem stimulator listrik beserta keluaran pulsa menuju elektroda stimulasi. Ardhya Novri Ramadhan menyelesaikan akuisisi dan pemrosesan digital sinyal *sEMG* dari sensor hingga menjadi data aktivitas otot. Tsaqif Zain Khan Bhadrika menyelesaikan sistem kendali dan GUI yang menerima data, menampilkan kondisi sistem, serta mengatur keputusan kendali. Pembagian kerja tersebut dirangkum pada Tabel 3.1.

Tabel 3.1 Pembagian kerja sistem alat rehabilitasi tangan.

| **No.** | **Anggota** | **Fokus perancangan** | **Keluaran utama** |
| --- | --- | --- | --- |
| 1 | Aldin Zahwan | Perancangan subsistem stimulator listrik | Pulsa stimulasi listrik menuju elektroda stimulasi |
| 2 | Ardhya Novri Ramadhan | Akuisisi dan pemrosesan digital sinyal aktivitas otot | Data aktivitas otot sebagai masukan subsistem kendali |
| 3 | Tsaqif Zain Khan Bhadrika | Perancangan sistem kendali dan aplikasi GUI | Keputusan kendali dan tampilan pemantauan sistem |

Ketiga bagian diintegrasikan melalui pertukaran data dan perintah antarsubsistem. Keluaran pemrosesan *sEMG* menjadi masukan bagi GUI dan kendali, sedangkan keluaran kendali menjadi perintah bagi stimulator. Batas tanggung jawab setiap anggota digunakan agar pembahasan individual tetap terarah tanpa memutus hubungan dengan sistem *capstone* secara keseluruhan.

## Analisis Kebutuhan Subsistem Pemrosesan Sinyal Aktivitas Otot

Subsistem akuisisi dan pemrosesan digital *sEMG* menerima keluaran analog SEN0240, mengubahnya menjadi data digital melalui ADC STM32F411CEU6, mengoreksi *offset*, menapis sinyal, membentuk fitur amplitudo, lalu mengirimkan hasilnya melalui UART. Gambar 3.2 memperlihatkan hubungan setiap tahap.

![](data:image/jpeg;base64...)

Gambar 3.2 Diagram alir akuisisi, pemrosesan, telemetri, dan penyajian sinyal EMG.

Kebutuhan subsistem diturunkan dari keluaran sensor dan teori pada Bab II. ADC menyediakan deret sampel, Butterworth membatasi pita pengamatan, takik memberi pelemahan selektif sekitar 50 Hz, dan RMS serta MAV merangkum amplitudo. UART menyediakan jalur keluaran menuju GUI. Tabel 3.2 menjelaskan fungsi setiap tahap. Ukuran evaluasinya pada Tabel 3.17 membedakan konfigurasi rancangan, hasil yang tercatat, dan aspek yang memerlukan pengukuran tersendiri.

Tabel 3.2 Kebutuhan subsistem pemrosesan sinyal aktivitas otot.

| **No.** | **Kebutuhan** | **Alasan** | **Penerapan pada penelitian** |
| --- | --- | --- | --- |
| 1 | Akuisisi sinyal analog | Keluaran SEN0240 berupa tegangan analog | Dibaca melalui ADC1 *pin* PA0 |
| 2 | Frekuensi pencuplikan | Rentang EMG mencapai 500 Hz | Konfigurasi nominal 4000 Hz |
| 3 | Kalibrasi dan koreksi *offset* | Keluaran memiliki bias tegangan pada kondisi relaks | *Offset* dihitung dan dikurangkan dari data ADC |
| 4 | Pengurangan frekuensi rendah | Artefak dapat muncul pada frekuensi rendah | Tapis lolos-tinggi Butterworth 20 Hz |
| 5 | Pembatasan frekuensi tinggi | Membatasi pita pengamatan hingga 500 Hz | Tapis lolos-rendah Butterworth 500 Hz |
| 6 | Penekanan gangguan 50 Hz | Komponen sekitar 50 Hz berada dalam pita pengamatan | Tapis takik digital 50 Hz |
| 7 | Ekstraksi fitur | Sinyal masih berupa deretan sampel | Perhitungan RMS dan MAV |
| 8 | Pengiriman data | Data diteruskan ke aplikasi GUI | Komunikasi UART |
| 9 | Penyajian aktivitas otot | Nilai perlu ditampilkan lebih stabil | Pengolahan tampilan pada GUI anggota lain |

## Alat dan Bahan Subsistem Pemrosesan Sinyal EMG

Subsistem memakai STM32F411CEU6 berbasis ARM Cortex-M4 dengan FPU dan ADC 12-bit [15]. Tabel 3.3 memuat perangkat keras untuk akuisisi, pemrosesan, catu daya, dan pemeriksaan rangkaian EMG. Daftar ini menjelaskan peran setiap perangkat dalam pengujian subsistem.

Tabel 3.3 Perangkat keras untuk akuisisi, pemrosesan, dan pengujian sinyal EMG.

| **No.** | **Perangkat keras** | **Fungsi** |
| --- | --- | --- |
| 1 | Sensor elektromiografi DFRobot SEN0240 | Mengubah aktivitas listrik otot menjadi sinyal tegangan analog |
| 2 | Elektroda kering | Menghubungkan permukaan kulit dengan sensor elektromiografi |
| 3 | Mikrokontroler STM32F411CEU6 | Membaca sinyal melalui ADC dan melakukan pemrosesan digital |
| 4 | Laptop | Menjalankan aplikasi GUI, pemrograman, dan pemantauan data |
| 5 | Multimeter | Mengukur tegangan dan memeriksa hubungan rangkaian |
| 6 | Catu daya atau baterai | Menyediakan sumber tegangan bagi perangkat |

Pengembangan sistem memerlukan perangkat lunak untuk menyiapkan konfigurasi, menulis program, menganalisis respons tapis, dan mengolah data. Tabel 3.4 membedakan fungsi setiap perangkat lunak agar perannya dalam proses perancangan dapat ditelusuri.

Tabel 3.3 Perangkat lunak yang digunakan.

| **No.** | **Perangkat lunak** | **Fungsi** |
| --- | --- | --- |
| 1 | STM32CubeMX | Mengatur konfigurasi ADC, *timer*, dan komunikasi UART |
| 2 | STM32CubeIDE | Menulis, membangun, dan mengunggah program ke STM32F411CEU6 |
| 3 | MATLAB | Membantu perancangan dan analisis respons tapis digital |
| 4 | Visual Studio Code | Mengembangkan aplikasi GUI dan komunikasi serial |
| 5 | Python | Mengolah dan menampilkan data sinyal pada aplikasi GUI |

## Perancangan Perangkat Keras dan Akuisisi Sinyal

Keluaran SEN0240 dihubungkan ke PA0 sebagai ADC1\_IN0 pada STM32F411CEU6. ADC dipicu oleh pembaruan TIM2 melalui TRGO; DMA memindahkan hasil konversi. Dengan clock TIM2 84 MHz, prescaler 83, dan autoreload 249, frekuensi pemicu nominal ialah 84.000.000/[(83 + 1)(249 + 1)] = 4.000 Hz. Perhitungan ini memverifikasi konfigurasi timer. Frekuensi pencuplikan aktual dan variasi periodenya memerlukan pengukuran waktu eksternal.

![](data:image/png;base64...)

Gambar 3.3 Hubungan sensor DFRobot SEN0240 dengan ADC STM32F411CEU6.

Pada Gambar 3.3, SEN0240 diberi catu 3,3 V dan GND. Keluaran analognya, sekitar 0 sampai 3,0 V, masuk ke PA0 yang dikonfigurasi sebagai ADC1\_IN0. Sinyal tersebut sudah melewati pengondisi internal SEN0240, mikrokontroler tidak membaca sinyal elektroda secara langsung.

Frekuensi pencuplikan 4.000 Hz menyediakan delapan sampel per periode pada batas pengamatan 500 Hz dan frekuensi Nyquist nominal 2.000 Hz. Jarak tersebut memberi ruang antara pita pengamatan dan Nyquist sesuai Subbab 2.6. Pengondisi SEN0240 bekerja sebelum ADC, sedangkan tapis digital bekerja setelahnya. Karena respons analog di atas Nyquist belum diukur, konfigurasi ini tidak menjadi bukti penolakan aliasing seluruh jalur. Tabel 3.5 memuat parameter akuisisi.

Tabel 3.4 Parameter akuisisi sinyal dan pembacaan ADC.

| **Parameter** | **Nilai** | **Keterangan** |
| --- | --- | --- |
| Mikrokontroler | STM32F411CEU6 | Perangkat pembaca dan pemroses sinyal |
| ADC | ADC1 | Mengubah sinyal analog menjadi data digital |
| *Pin* masukan | PA0 | Terhubung dengan keluaran sensor SEN0240 |
| Resolusi ADC | 12-bit | Menghasilkan 4096 tingkat kuantisasi |
| Tegangan referensi | 3,3 V | Nilai nominal untuk konversi kode ADC |
| Frekuensi pencuplikan | 4000 Hz | Konfigurasi nominal, belum diukur dengan acuan eksternal |

Konfigurasi menetapkan interval pencuplikan nominal 0,25 ms. Konversi program menggunakan Persamaan 2.1 dan 2.2 dengan resolusi 12 bit serta tegangan referensi nominal 3,3 V. Substitusi parameter menghasilkan skala 3,3/4095 V per kode, yaitu sekitar 0,806 mV per kode pada masukan ADC. Setelah dikonversi, data masuk ke tahap kalibrasi dan koreksi offset sebelum penapisan digital. Seluruh amplitudo dalam mV pada Bab IV memakai skala ekuivalen masukan ADC setelah penguatan sensor. Nilai tersebut tidak menyatakan potensial elektroda sebelum penguatan atau gaya genggaman.

## Perancangan *Filter* Digital Butterworth dan Takik

Perancangan menetapkan batas frekuensi, orde, dan koefisien berdasarkan Subbab 2.7 dan 2.8. Kaskade terdiri atas Butterworth lolos tinggi 20 Hz, lolos rendah 500 Hz, dan takik 50 Hz. Pengondisi SEN0240 menyediakan masukan analog, sedangkan tahap digital menetapkan respons tambahan yang koefisiennya dapat diperiksa. Evaluasi antartahap diperlukan untuk menilai perubahan yang benar-benar terjadi setelah ADC, termasuk pelemahan komponen sinyal yang berada di daerah redam.

### Perancangan Butterworth Lolos Tinggi dan Lolos Rendah

Butterworth dirancang sebagai dua bagian orde dua yang diproses berurutan, yaitu lolos tinggi 20 Hz dan lolos rendah 500 Hz. Pemilihan batas mengikuti pita pengamatan *sEMG* dan keluaran SEN0240. Fungsi alih serta koefisien setiap bagian ditentukan dari Persamaan 2.6 sampai 2.12.

Bentuk pembatasan pita rancangan dapat ditinjau melalui kurva magnitudo pada Gambar 3.4. Kurva ini menjadi acuan respons sebelum koefisien diterapkan pada mikrokontroler.

![](data:image/png;base64...)

Gambar 3.4 Respons magnitudo teoretis koefisien rancangan HPF, LPF, dan takik 50 Hz.

Gambar 3.4 memperlihatkan respons yang dihitung dari koefisien rancangan, bukan hasil pengukuran pada STM32F411CEU6. HPF melemahkan komponen di bawah 20 Hz, LPF melemahkan komponen di atas 500 Hz, dan takik menargetkan 50 Hz. Pada batas 20 Hz dan 500 Hz, respons Butterworth turun sekitar 3 dB. Kurva ini menjadi acuan pengujian pada Bab IV.

HPF orde dua dan LPF orde dua membentuk kaskade berorde total empat. Responsnya dihitung sebagai perkalian kedua fungsi alih, bukan dianggap sama dengan satu rancangan band-pass Butterworth dari transformasi prototipe. Takik orde dua menambah satu biquad sehingga jalur lengkap berorde total enam. Tabel 3.6 merangkum struktur Butterworth yang digunakan.

Tabel 3.5 Parameter tapis digital Butterworth.

| **Parameter** | **Nilai** | **Keterangan** |
| --- | --- | --- |
| Frekuensi pencuplikan | 4000 Hz | Laju nominal untuk perancangan koefisien |
| Tapis lolos-tinggi | Butterworth orde 2 | Tahap pertama |
| Frekuensi batas lolos tinggi | 20 Hz | Mengurangi komponen frekuensi rendah |
| Tapis lolos-rendah | Butterworth orde 2 | Tahap kedua |
| Frekuensi batas lolos rendah | 500 Hz | Membatasi komponen frekuensi tinggi |
| Orde total HPF dan LPF | 4 | Gabungan HPF orde 2 dan LPF orde 2 |
| Struktur implementasi | IIR *biquad* | Diproses secara berurutan |
| Presisi numerik | *Floating point* 32-bit | Menggunakan tipe data *float* pada STM32 |

Batas 20–500 Hz mengikuti pita keluaran SEN0240 [14] dan acuan pemrosesan sEMG [10]. Butterworth menyediakan magnitudo tanpa riak pada pita lolos ideal. Setiap bagian orde dua memerlukan satu biquad dengan dua keadaan, sehingga jumlah keadaan dan operasi per sampel dapat dibatasi. Alasan ini menjelaskan pilihan struktur. Penelitian mengevaluasi respons pilihan tersebut tanpa menyatakan keunggulan terhadap FIR, keluarga IIR lain, atau orde yang belum dibandingkan secara terukur.

Normalisasi berdasarkan Persamaan 2.7 menggunakan frekuensi Nyquist 2.000 Hz. Hasil pada Tabel 3.7 menempatkan batas HPF pada Wn = 0,01 dan batas LPF pada Wn = 0,25. Nilai ini menjadi masukan perancangan dalam skala frekuensi ternormalisasi yang dapat dilihat pada Tabel 3.7.

Tabel 3.6 Normalisasi frekuensi batas tapis Butterworth.

| **Jenis tapis** | **Frekuensi batas** | **Perhitungan** | **Nilai ternormalisasi** |
| --- | --- | --- | --- |
| Lolos tinggi | 20 Hz | 20/2000 | 0,01 |
| Lolos rendah | 500 Hz | 500/2000 | 0,25 |

Koefisien dihitung menggunakan Persamaan 2.11 dan 2.12. Nilai K = tan(πfc/fs) sebesar 0,0157093 untuk HPF dan 0,4142136 untuk LPF. Dengan D = 1 + √2K + K², hasil normalisasi membentuk koefisien b0, b1, b2, a1, dan a2 pada Tabel 3.8.

Kolom HPF dan LPF pada Tabel 3.8 memisahkan lima koefisien setiap tahap. Penyajian ini memudahkan pencocokan nilai rancangan dengan nilai yang digunakan pada *firmware*.

Tabel 3.7 Koefisien tapis Butterworth pada *firmware*.

| **Koefisien** | **HPF 20 Hz orde 2** | **LPF 500 Hz orde 2** |
| --- | --- | --- |
| b0 | 0,9780304792 | 0,0976310729 |
| b1 | −1,9560609584 | 0,1952621459 |
| b2 | 0,9780304792 | 0,0976310729 |
| a1 | −1,9555782403 | −0,9428090416 |
| a2 | 0,9565436765 | 0,3333333333 |

Koefisien pada Tabel 3.8 menghasilkan magnitudo pole sekitar 0,978 untuk HPF dan 0,577 untuk LPF. Keduanya berada di dalam lingkaran satuan, sehingga fungsi alih linear tersebut memenuhi syarat kestabilan. Program menggunakan float 32 bit. Pemeriksaan pole menjelaskan kestabilan model, sedangkan catatan kesalahan numerik pada sesi uji memberi informasi tambahan tentang pelaksanaan pemrosesan.

### Perancangan Tapis Takik 50 Hz

Takik dirancang setelah HPF dan LPF untuk menekan komponen di sekitar 50 Hz. Perancangan mengacu pada Subbab 2.8 dengan frekuensi tengah 50 Hz, faktor kualitas 30, dan laju pencuplikan 4.000 Hz.

Gambar 3.5 memperlihatkan bentuk takik yang dipusatkan pada 50 Hz. Daerah redam dibuat sempit untuk membatasi perubahan komponen EMG di sekitar frekuensi sasaran.

![](data:image/png;base64...)

Gambar 3.4 Respons magnitudo tapis takik pada frekuensi 50 Hz.

Cekungan respons pada Gambar 3.5 terpusat di sekitar 50 Hz, sementara frekuensi di luarnya mendekati daerah lolos. Faktor kualitas Q = 30 mengatur selektivitas tersebut. Tabel 3.9 menghubungkan pilihan frekuensi tengah, faktor kualitas, dan perkiraan lebar pita dengan posisi takik dalam kaskade.

Tabel 3.8 Parameter perancangan tapis takik digital.

| **Parameter** | **Nilai** | **Keterangan** |
| --- | --- | --- |
| Frekuensi pencuplikan | 4000 Hz | Laju nominal untuk perancangan koefisien |
| Jenis tapis | IIR takik | Melemahkan frekuensi tertentu |
| Orde tapis | 2 | Diimplementasikan sebagai satu *biquad* |
| Frekuensi tengah | 50 Hz | Frekuensi utama yang dilemahkan |
| *Quality factor* Q | 30 | Menentukan lebar daerah takik |
| Perkiraan *bandwidth* | 1,67 Hz | Diperoleh dari 50/30 |
| Masukan tapis | Keluaran Butterworth | Sinyal setelah HPF dan LPF |
| Keluaran tapis | Sinyal EMG terfilter | Digunakan untuk RMS dan MAV |

Penerapan Persamaan 2.15 dan 2.16 menghasilkan ω0 = 0,07854 rad/sampel serta BW = 50/30 = 1,67 Hz. Persamaan 2.17 menghasilkan β = 0,0013090 dan g = 0,9986927. Nilai tersebut digunakan pada Persamaan 2.18 untuk memperoleh koefisien takik.

Koefisien hasil substitusi parameter dihimpun pada Tabel 3.10. Pasangan nilai b0 dan b2 yang sama serta b1 = a1 mengikuti bentuk takik pada Persamaan 2.18.

Tabel 3.9 Koefisien tapis takik 50 Hz pada *firmware*.

| **Koefisien** | **Nilai** |
| --- | --- |
| b0 | 0,9986927135 |
| b1 | −1,9912281544 |
| b2 | 0,9986927135 |
| a1 | −1,9912281544 |
| a2 | 0,9973854271 |

Koefisien pada Tabel 3.10 digunakan untuk tapis takik orde dua dengan f0 = 50 Hz, Q = 30, dan fs = 4000 Hz. Masukannya adalah keluaran HPF dan LPF, sedangkan hasilnya menjadi sinyal akhir untuk ekstraksi fitur. Magnitudo *pole* tapis sekitar 0,9987 dan masih berada di dalam lingkaran satuan. Karena itu, tapis takik stabil secara teoritis.

Respons koefisien dievaluasi pada frekuensi tengah dan posisi puncak yang teramati dalam rekaman. Perbandingan pada bin nominal 51 Hz dan 102 Hz menjelaskan akibat selektivitas terhadap data tersebut. Titik evaluasi ini tidak mengubah frekuensi tengah rancangan yang tetap 50 Hz.

Q = 30 menghasilkan lebar pita perkiraan 1,67 Hz. Takik yang sempit membatasi perubahan frekuensi di luar sasaran, tetapi juga membuat redaman berkurang ketika komponen gangguan menjauh dari pusat takik. Komponen sEMG yang berada pada frekuensi sasaran ikut dilemahkan. Evaluasi karena itu memeriksa besar pelemahan dan sisa komponen pada rekaman, tanpa menyamakan kesesuaian koefisien dengan pemisahan sempurna antara sEMG dan gangguan.

## Perancangan Perangkat Lunak Pemrosesan Sinyal EMG

Perhitungan konfigurasi TIM2 memberi 4.000 pemicu per detik secara nominal. Validasi laju pencuplikan memerlukan keluaran pulsa uji yang mengikuti pembaruan TIM2 dan pengukuran periode dengan osiloskop atau pencacah waktu independen. Periode targetnya 250 µs. Distribusi selang pulsa diperlukan untuk menilai jitter, sedangkan perbandingan jumlah sampel dan durasi rekaman independen dapat memeriksa sampel yang terlewat. Data pengujian ini belum memuat pengukuran tersebut, sehingga 4.000 Hz tetap dilaporkan sebagai konfigurasi nominal.

### Perancangan Kalibrasi dan Koreksi *Offset*

Kalibrasi offset menghitung rata-rata 8.000 sampel valid saat otot relaks, setara 2 detik secara nominal pada 4.000 Hz. Kode EMG yang diperiksa juga menetapkan 2.000 sampel awal untuk penstabilan sensor. Karena itu, durasi pengumpulan sampel valid tidak sama dengan waktu total sejak perangkat mulai bekerja. Program menyimpan rata-rata kode ADC sebagai adc\_offset\_counts, mengurangkannya dari setiap sampel, lalu menerapkan skala tegangan pada Persamaan 2.1.

Rata-rata kalibrasi menentukan titik nol untuk mengurangi bias keluaran sensor. Proses tersebut tidak mengalibrasi penguatan sensor, skala gaya, atau ketelitian tegangan. Tabel 3.11 merangkum parameter koreksi offset. Nilai offset disimpan dan tidak dihitung ulang pada setiap jendela RMS/MAV. HPF tetap diperlukan untuk memberi pembatasan frekuensi rendah ketika garis dasar berubah setelah kalibrasi.

Tabel 3.10 Parameter kalibrasi dan koreksi *offset*.

| **Parameter** | **Keterangan** |
| --- | --- |
| Kondisi kalibrasi | Otot dalam keadaan relaks |
| Data masukan | Nilai hasil pembacaan ADC |
| Metode penentuan *offset* | Rata-rata sampel kalibrasi |
| Proses koreksi | Pengurangan nilai ADC terhadap *offset* |
| Keluaran | Sinyal terkoreksi sebelum penapisan digital |
| Jumlah sampel kalibrasi | 8000 sampel |
| Durasi kalibrasi *offset* | 2 detik nominal untuk 8.000 sampel valid, di luar penstabilan awal. |

### Implementasi Kaskade Tapis Digital

Fungsi Biquad\_Process pada Core/Src/emg\_app.c menerapkan Persamaan 2.10 dalam bentuk *Direct Form II Transposed*. Setiap tahap memakai objek dengan koefisien dan dua keadaan tersendiri.

static float Biquad\_Process(BiquadDF2T \*filter, float input)
{
 float output = (filter->b0 \* input) + filter->state1;

 filter->state1 =
 (filter->b1 \* input) - (filter->a1 \* output)
 + filter->state2;
 filter->state2 =
 (filter->b2 \* input) - (filter->a2 \* output);

 return output;
}

Variabel output dihitung dari masukan saat ini dan state 1. Program kemudian memperbarui kedua keadaan untuk sampel berikutnya. Struktur yang sama digunakan oleh HPF, LPF, dan takik dengan objek serta koefisien masing-masing. Dua keadaan tapis tidak direset pada setiap batas jendela RMS dan MAV.

Bagian Process\_ADC\_Block berikut menghubungkan hasil ADC dengan penapisan setiap sampel. ADC\_TO\_VOLT mengubah selisih kode ADC terhadap offset menjadi tegangan ekuivalen pada masukan ADC.

const float raw\_centered =
 ((float)sample - adc\_offset\_counts) \* ADC\_TO\_VOLT;

const float highpass\_output =
 Biquad\_Process(&highpass\_filter, raw\_centered);
const float bandpass\_output =
 Biquad\_Process(&lowpass\_filter, highpass\_output);
const float filtered\_output =
 Biquad\_Process(&notch\_filter, bandpass\_output);

Keluaran highpass\_filter menjadi masukan lowpass\_filter, lalu hasilnya melewati notch\_filter. Dengan demikian, bandpass\_output menunjukkan hasil Butterworth sebelum takik, sedangkan filtered\_output menunjukkan hasil akhir. Pemisahan titik data ini memungkinkan perbandingan setiap tahap. Pemeriksaan batas numerik, pencatatan *buffer*, dan pemanggilan ekstraksi fitur berada pada bagian lanjutan fungsi yang tidak ditampilkan dalam potongan ini.

### Perancangan Ekstraksi Fitur RMS dan MAV

Sistem menghitung RMS dan MAV dari 400 sampel tanpa overlap. Pada frekuensi nominal 4.000 Hz, satu jendela memuat 100 ms dan menghasilkan paling banyak 10 pembaruan fitur per detik. Pilihan ini memberi nilai amplitudo yang lebih ringkas daripada sampel mentah dan membatasi laju pembaruan GUI. Penelitian ini tidak membandingkan beberapa panjang jendela, sehingga 100 ms merupakan parameter rancangan, bukan hasil optimasi.

Sampel yang baru masuk menunggu antara hampir 0 dan 100 ms hingga batas jendela berikutnya, bergantung posisinya dalam jendela. Sesudah itu, pemrosesan, antrean UART, penerimaan, dan penggambaran GUI masih membutuhkan waktu. Karena waktu tahap tersebut tidak diukur secara sinkron, latensi ujung ke ujung belum dapat dihitung dari durasi jendela atau interval pencatatan GUI.

RMS dipakai sebagai keluaran utama karena menyatakan nilai efektif sinyal dalam satu jendela menurut Persamaan 2.21. MAV pada Persamaan 2.22 menyediakan pembanding dengan pembobotan amplitudo absolut. Keduanya berasal dari sampel yang sama. Perbandingan tersebut menilai karakter fitur dan tidak menjadi validasi independen terhadap gaya. Tabel 3.12 memuat parameter ekstraksi.

Tabel 3.11 Parameter ekstraksi fitur sinyal EMG.

| **Parameter** | **Nilai** | **Keterangan** |
| --- | --- | --- |
| Data masukan | Sinyal hasil penapisan | Keluaran tapis takik 50 Hz |
| Frekuensi pencuplikan | 4000 Hz | Konfigurasi nominal akuisisi |
| Durasi jendela | 100 ms | Durasi nominal 400 sampel |
| Jumlah sampel | 400 sampel | Data dalam satu jendela pengamatan |
| Metode ekstraksi | RMS dan MAV | Merepresentasikan amplitudo aktivitas otot |
| Keluaran fitur | RMS dan MAV | RMS digunakan sebagai parameter utama keluaran, MAV sebagai parameter pendukung analisis |

Penerapan Persamaan 2.20 dengan fs = 4.000 Hz dan Tw = 0,1 detik menghasilkan N = 400 sampel. Program menetapkan FEATURE\_WINDOW\_SAMPLES sebesar 400 dan memakai jendela tanpa *overlap*. Urutan pada Tabel 3.13 memperjelas bahwa satu pasangan RMS dan MAV baru diterbitkan setelah seluruh sampel jendela terkumpul.

Tabel 3.12 Tahapan ekstraksi fitur sinyal EMG.

| **Tahap** | **Proses** | **Hasil** |
| --- | --- | --- |
| 1 | Menerima sinyal hasil penapisan | Keluaran kaskade HPF, LPF, dan takik |
| 2 | Mengumpulkan 400 sampel | Jendela nominal 100 ms |
| 3 | Menghitung RMS | Nilai efektif sinyal EMG |
| 4 | Menghitung MAV | Rata-rata amplitudo absolut |
| 5 | Menyiapkan data keluaran | Nilai RMS diteruskan sebagai parameter utama, sedangkan MAV disimpan sebagai parameter analisis |

RMS menjadi keluaran utama, sedangkan MAV disimpan sebagai data pembanding. Gambar 3.6 merangkum alur akuisisi, penapisan, ekstraksi fitur, dan pengiriman data.

![](data:image/png;base64...)

Gambar 3.5 Diagram alir implementasi pemrosesan sinyal EMG pada STM32F411CEU6.

Percabangan pada Gambar 3.6 memisahkan pemrosesan setiap sampel dari pembaruan fitur. ADC, *timer* 4 kHz, dan UART diinisialisasi sebelum kalibrasi *offset*. Sampel terkoreksi melewati HPF 20 Hz, LPF 500 Hz, dan takik 50 Hz. RMS serta MAV dihitung ketika jumlah sampel mencapai 400. Setelah pengiriman keluaran, indeks jendela diatur ulang untuk pengumpulan berikutnya.

Potongan terpilih dari Update\_Features berikut memperlihatkan akumulasi dan pembaruan RMS serta MAV hasil penapisan. FEATURE\_WINDOW\_SAMPLES bernilai 400. Baris untuk fitur sebelum penapisan, penanganan kesalahan, dan penyimpanan tambahan diringkas dengan komentar.

filtered\_square\_sum += filtered\_value \* filtered\_value;
filtered\_absolute\_sum += fabsf(filtered\_value);
feature\_sample\_count++;
if (feature\_sample\_count >= FEATURE\_WINDOW\_SAMPLES)
{
 const float divisor = (float)feature\_sample\_count;
 const float next\_filtered\_rms =
 sqrtf(filtered\_square\_sum / divisor);
 const float next\_filtered\_mav =
 filtered\_absolute\_sum / divisor;
 /\* Perhitungan fitur lain dan validasi tidak ditampilkan. \*/
 filtered\_rms\_100ms = next\_filtered\_rms;
 filtered\_mav\_100ms = next\_filtered\_mav;
 filtered\_rms\_mV = next\_filtered\_rms \* 1000.0f;
 filtered\_mav\_mV = next\_filtered\_mav \* 1000.0f;
 /\* Reset akumulator raw dan bandpass tidak ditampilkan. \*/
 filtered\_square\_sum = 0.0f;
 filtered\_absolute\_sum = 0.0f;
 feature\_sample\_count = 0U;
 feature\_update\_count++;
}

Akumulator kuadrat menghasilkan RMS, sedangkan akumulator nilai absolut menghasilkan MAV. Perkalian 1000 mengubah satuan volt menjadi milivolt pada keluaran sensor yang dibaca ADC, bukan tegangan langsung pada elektroda sebelum penguatan sensor. Setelah fitur diterbitkan, akumulator dan pencacah jendela direset. Pencacah feature\_update\_count bertambah sekali per jendela dan dapat digunakan untuk membedakan pembaruan fitur dari baris pencatatan yang berulang.

### Perancangan Telemetri UART dan Pengolahan Data pada GUI

Pada log pengujian UART, format data mentah berupa EMG\_RMS\_MV,<nilai>, misalnya EMG\_RMS\_MV,31.96. Nilai menyatakan RMS terfilter dalam mV pada skala masukan ADC. Jalur serial menghubungkan UART mikrokontroler dengan penerima pada komputer. Tabel 3.14 menunjukkan alur penerimaan dan pengolahan fitur tersebut.

Tabel 3.13 Tahapan telemetri UART dan pengolahan data pada GUI.

| **Tahap** | **Proses** | **Hasil** |
| --- | --- | --- |
| 1 | Menyiapkan nilai RMS terfilter | RMS dalam mV ekuivalen masukan ADC |
| 2 | Mengirim data melalui UART TX | Nilai RMS dikirim melalui jalur serial |
| 3 | Menerima data serial pada komputer | Data diterima aplikasi GUI |
| 4 | Melakukan validasi data | Data numerik yang dapat diproses |
| 5 | Menghaluskan data menggunakan EMA | Nilai tampilan setelah penghalusan |
| 6 | Menggunakan nilai referensi *baseline* | Acuan tampilan, terpisah dari offset ADC |
| 7 | Menyajikan status aktivitas | Informasi aktivitas otot pada GUI |

GUI menerima RMS, menerapkan Exponential Moving Average (EMA), dan menggunakan baseline untuk penyajian aktivitas. Baseline tampilan berbeda dari offset ADC yang digunakan sebelum penapisan. Evaluasi individu memeriksa data pada batas antarmuka dan hasil pengolahan yang tercatat. Kolom sequence terpisah dari raw\_line dan tidak digunakan sebagai pencacah paket STM32. Perancangan GUI serta keputusan kendali tetap menjadi kontribusi anggota lain.

## Prosedur Pengujian dan Pengambilan Data

Pengujian menjawab tujuan pada Subbab 1.3 melalui pemeriksaan konfigurasi, respons tapis, fitur amplitudo, dan penerimaan UART. Sesi fitur kontinu, rekaman raw, dan sesi UART merupakan kelompok bukti yang berbeda. Statistik fitur merangkum keluaran per jendela, pasangan raw menilai respons digital, dan log UART menilai data yang diterima. Satu rekaman raw memuat 8.000 record berisi empat nilai 16 bit, sehingga payload berukuran 64.000 byte.

Seluruh pengujian melibatkan penulis sebagai satu-satunya subjek dan menggunakan lengan bawah kiri. Posisi sensor dijaga selama satu sesi. Nama otot, jarak elektroda terhadap penanda anatomi, dan koordinat pemasangan tidak dicatat secara terukur. Rekaman kontinu berlangsung satu kali sekitar 10 menit, sedangkan rekaman *raw* terdiri atas rekaman terpisah berdurasi 2 detik.

Data RMS dan MAV merupakan hasil pengolahan setiap 100 ms, sedangkan analisis bentuk gelombang dan frekuensi memerlukan sampel *raw*. Titik pengambilan data dirangkum pada Tabel 3.15.

Tabel 3.14 Titik pengambilan data pada pengujian subsistem EMG.

| **Titik data** | **Data yang diamati** | **Tujuan** |
| --- | --- | --- |
| Data 1 | Sinyal setelah koreksi *offset* | Mengamati sinyal sebelum penapisan digital |
| Data 2 | Sinyal setelah HPF dan LPF Butterworth | Mengevaluasi penapisan rentang 20–500 Hz |
| Data 3 | Sinyal setelah tapis takik | Mengevaluasi penekanan komponen sekitar 50 Hz |
| Data 4 | Nilai RMS dan MAV | Mengamati perubahan aktivitas otot |
| Data 5 | Data yang diterima aplikasi | Memastikan hasil pemrosesan dapat diteruskan melalui UART |

Statistik sesi kontinu menggunakan baris pertama untuk setiap nilai feature\_update\_count yang berbeda pada lembar Raw Data. Waktu relatif dihitung dengan mengurangkan waktu baris pertama, yaitu 98,733 detik. Nilai fitur dalam volt dikalikan 1.000 sebelum dilaporkan dalam mV. Rata-rata pada Tabel 4.2, 4.4, dan 4.5 merupakan rata-rata fitur per jendela 400 sampel. Sebaliknya, RMS tiap rekaman pada Tabel 4.6 dihitung langsung dari seluruh 8.000 sampel notch\_v. Kedua ukuran memiliki durasi perataan berbeda.

Setiap record raw memuat adc\_raw, hpf\_q, bandpass\_q, dan notch\_q. Nilai bertanda q memakai skala 10.000 hitungan per volt, setara langkah representasi 0,1 mV. Metadata memuat first\_sample, jumlah record, offset, status, serta CRC-32 payload. Indeks sample\_index pada CSV dibentuk dari first\_sample ditambah posisi record, sehingga kesinambungan indeks tersebut bukan pengukuran waktu pencuplikan independen. Data 4 memuat fitur sesi kontinu, sedangkan Data 5 memuat log penerimaan UART.

Evaluasi Butterworth memakai adc\_centered\_v sebagai masukan dan bandpass\_v sebagai keluaran. Kedua titik telah melewati sensor serta ADC yang sama. Perbandingan ini memisahkan perubahan akibat HPF dan LPF dari pengondisian analog sebelumnya. Hasilnya menjelaskan karakteristik tahap digital pada data tersimpan. Respons sensor secara keseluruhan dan keunggulan sistem dibandingkan sensor tanpa pemrosesan tambahan memerlukan pengujian berbeda.

Perbandingan usaha memakai empat kelompok arsip, yaitu RELAX, LIGHT, MEDIUM\_RPE5, dan STRONG, masing-masing tiga rekaman berisi 8.000 sampel. Durasi setiap rekaman setara 2 detik pada laju nominal 4.000 Hz. Tabel 3.16 mempertahankan nama kelompok agar hasil dapat ditelusuri ke berkas sumber. Label tersebut merupakan pengelompokan operasional rekaman.

Tabel 3.15 Kelompok rekaman raw untuk perbandingan usaha.

| **Kondisi** | **Acuan aktivitas** | **Pengulangan** | **Durasi nominal** |
| --- | --- | --- | --- |
| Relaks | Otot dalam kondisi rileks | 3 | 2 s |
| Ringan | Genggaman dengan usaha ringan | 3 | 2 s |
| Sedang RPE 5 | Label arsip MEDIUM\_RPE5, bukan kategori sedang baku Borg | 3 | 2 s |
| Kuat | Instruksi genggaman kuat, tanpa pembanding gaya | 3 | 2 s |

Nama sedang RPE 5 merujuk pada arsip MEDIUM\_RPE5. Pada Borg CR10, angka 5 berlabel kuat, sedangkan sedang berada pada angka 3 [17], [23]. Karena itu, label sedang dalam arsip tidak diperlakukan sebagai kategori baku Borg atau titik tengah gaya. Instruksi ringan dan kuat juga tidak disertai pengukuran gaya. Perbandingan dibatasi pada kelompok rekaman yang tersedia, dengan posisi lengan dan sensor dijaga sejauh memungkinkan. Jeda antarpengulangan tidak dicatat secara terukur.

Tiga pengulangan menghasilkan tiga nilai RMS rekaman untuk statistik tiap kelompok. Nilai rata-rata, standar deviasi, dan koefisien variasi menggambarkan pengulangan pada satu subjek. Sampel dalam rekaman tidak diperlakukan sebagai subjek independen. Analisis bersifat deskriptif dan tidak menetapkan perbedaan populasi atau urutan gaya berdasarkan label usaha.

Tabel 3.17 menghubungkan tujuan dengan ukuran yang dapat dihitung. Evaluasi respons melaporkan gain serta pelemahan dalam dB, sedangkan evaluasi fitur dan UART melaporkan statistik data yang tercatat. Besaran tersebut dapat diperiksa tanpa menetapkan ambang kelulusan setelah melihat hasil. Kesesuaian respons dan kecukupan penekanan gangguan ditafsirkan sesuai ukuran masing-masing.

Respons Butterworth dihitung sebagai H1 = Sxy/Sxx dari adc\_centered\_v dan bandpass\_v, lalu dikonversi dengan 20 log10|H1| sesuai Persamaan 2.13 dan 2.14. Spektrum silang menggunakan konjugat transformasi masukan dikalikan transformasi keluaran. Analisis memakai jendela Hann periodik 4.000 sampel, overlap 2.000 sampel, FFT 4.000 titik, dan pengurangan rata-rata tiap segmen. Rekaman 8.000 sampel menghasilkan tiga segmen dengan awal 0, 2.000, dan 4.000. PSD satu sisi memakai normalisasi daya jendela yang sama pada bandpass\_v dan notch\_v. Jarak bin frekuensi sebesar 1 Hz pada skala pencuplikan nominal.

Seluruh 24 rekaman lengkap digunakan untuk evaluasi respons Butterworth. Tabel 4.6 memakai RELAX\_RAW\_01–03, LIGHT\_RAW\_01–03, MEDIUM\_RPE5\_RAW\_01–03, dan STRONG\_RAW\_01–03. Tiga POST\_RELAX\_RAW dipakai untuk mengamati komponen interferensi. MEDIUM\_RAW, MEDIUM\_RAW\_RETRY, dan pemeriksaan relaks tetap disertakan dalam evaluasi transfer. Pemilihan MEDIUM\_RPE5 mengikuti identitas kelompok pada arsip. Alasan serta waktu perubahan instruksinya belum terdokumentasi sebagai protokol awal. Lampiran B mempertahankan seluruh kelompok agar pemilihan data dapat diperiksa.

Statistik antarekaman menggunakan standar deviasi sampel dengan penyebut n − 1. Koefisien variasi dihitung sebagai 100% dikali standar deviasi dibagi rata-rata. Statistik ini menggambarkan variasi pada subjek yang sama. Estimator fungsi transfer bergantung pada daya masukan, keadaan awal tapis, kuantisasi rekaman, serta perataan spektrum. Jarak bin 1 Hz tidak sama dengan kemampuan memisahkan dua komponen berdekatan karena jendela Hann juga melebarkan puncak spektrum [19]. Analisis memakai seluruh sampel tersimpan dan belum menentukan ambang koherensi atau periode pembuangan transien. Tabel 3.17 memetakan ukuran terhadap tujuan.

Tabel 3.16 Hubungan tujuan penelitian, metode pengujian, dan tolok ukur.

| **Tujuan penelitian** | **Metode dan ukuran** | **Tolok ukur penilaian** |
| --- | --- | --- |
| Implementasi subsistem | Periksa konfigurasi, urutan HPF–LPF–takik, koefisien, jumlah sampel, dan pencacah fitur. | Periksa kesesuaian konfigurasi dan koefisien. Laporkan jumlah sampel, celah pencacah fitur, serta flag kesalahan dan clipping yang tercatat. |
| Evaluasi Butterworth | Bandingkan *gain* eksperimen dan teoritis pada 20 Hz, 500 Hz, pita lolos, dan pita redam menggunakan Persamaan 2.13–2.14. | Karakter pembatasan pita tampak. Selisih *gain* terhadap teori dilaporkan dalam dB. Respons batas tiap bagian mengacu sekitar −3,01 dB. |
| Evaluasi takik | Bandingkan PSD sebelum/sesudah pada interferensi dominan dan harmoniknya memakai Persamaan 2.19. | A(f) positif menunjukkan pelemahan. Besarnya dan selisih terhadap teori dilaporkan. Kesesuaian koefisien tidak otomatis membuktikan penekanan gangguan memadai. |
| Evaluasi RMS dan MAV | Bandingkan rata-rata, variasi pengulangan, dan hubungan RMS/MAV pada relaks serta variasi genggaman. | Laporkan kecenderungan rata-rata dan ketidakkonsistenan urutan kategori. Fitur tidak menjadi ukuran gaya absolut atau klasifikasi klinis. |
| Evaluasi penerimaan UART | Periksa raw\_line, filtered\_rms\_mv, jumlah baris, dan interval pencatatan log. | Nilai payload sesuai hasil parsing pada log. Kehilangan paket pemancar tidak ditentukan tanpa pencacah dari STM32. |

# BAB IV HASIL DAN PEMBAHASAN

## Hasil Implementasi dan Kondisi Pengujian

Subsistem menggunakan DFRobot SEN0240 untuk memperoleh sinyal dari lengan bawah kiri penulis sebagai satu-satunya subjek pengujian. STM32F411CEU6 melakukan pencuplikan ADC, koreksi *offset*, penapisan digital, dan perhitungan RMS serta MAV. Keluaran sensor masuk ke ADC, sedangkan laptop memantau dan mencatat hasil melalui komunikasi serial. Susunan perangkat dan pemasangan sensor ditunjukkan pada Gambar 4.1.

![](data:image/jpeg;base64...)

Gambar 4.1 Implementasi perangkat dan proses pengambilan data sinyal EMG.

Posisi sensor dipertahankan sejauh memungkinkan dan sistem melakukan kalibrasi saat otot relaks untuk memperoleh *offset*. Pengujian pertama menggunakan satu rekaman kontinu sekitar 10 menit, tanpa penghentian perekaman di antara kondisi relaks, genggaman ringan, sedang, kuat, dan perubahan posisi tangan. Pergantian kondisi terjadi di dalam rekaman yang sama.

Pengujian raw menghasilkan rekaman sinkron sebelum dan sesudah tahap digital, masing-masing 8.000 sampel pada konfigurasi 4.000 Hz. Analisis respons memakai seluruh 24 rekaman lengkap. Analisis usaha memakai tiga rekaman per kelompok sesuai Tabel 3.16. Kedua analisis menjawab pertanyaan berbeda, sehingga jumlah rekaman untuk evaluasi tapis tidak disamakan dengan jumlah pengulangan usaha.

## Hasil Akuisisi dan Kualitas Data EMG

Sesi kontinu berlangsung 602,10 detik dan menghasilkan 12.043 baris berisi MAV, RMS, serta parameter pemantauan. Kelengkapan urutan pembaruan, kesalahan, dan clipping diperiksa sebelum data dianalisis, hasilnya dirangkum pada Tabel 4.1.

Tabel 4.1 Hasil pemeriksaan akuisisi dan kualitas data EMG.

| **Parameter** | **Hasil** |
| --- | --- |
| Durasi perekaman | 602,10 s |
| Jumlah baris pencatatan | 12.043 baris |
| Jumlah pembaruan fitur unik | 5.901 data |
| Rentang feature\_update\_count | 20.780–26.680 |
| Celah nomor pembaruan pada log | 0 |
| Interval pencatatan utama | sekitar 0,05 s |
| Perkiraan interval fitur pada log | sekitar 0,1 s |
| emg\_*error*\_flags tidak nol | 0 |
| *clipping*\_percent\_1s lebih dari 0% | 0 |

Tabel 4.1 menunjukkan 5.901 nomor pembaruan fitur berurutan. Seluruh baris mencatat emg\_error\_flags = 0 dan clipping\_percent\_1s = 0. Hasil ini menyatakan tidak ada kejadian yang ditandai oleh kedua indikator pada log. Pencatatan sekitar 0,05 detik dapat mengulang fitur yang diperbarui sekitar 0,10 detik. Analisis memakai satu baris per nomor pembaruan agar satu fitur tidak mendapat bobot berulang.

Rasio 5.901 pembaruan unik terhadap durasi log 602,10 detik ialah sekitar 9,80 pembaruan per detik. Angka ini menggambarkan laju pembaruan yang tercatat di komputer, bukan frekuensi ADC, jitter pencuplikan, atau latensi pengiriman. Pencacah berurutan menunjukkan tidak ada celah nomor dalam log yang tersimpan. Validasi 4.000 Hz memerlukan pengukuran pemicu atau cap waktu sampel dengan acuan independen, seperti prosedur pada Subbab 3.5.

Dua puluh empat berkas raw masing-masing memuat 8.000 record. CRC-32 payload yang dihitung ulang cocok dengan metadata, dan hash SHA-256 berkas biner cocok dengan nilai arsip. Pemeriksaan ini mendukung integritas berkas yang tersimpan. Karena indeks sampel pada CSV hanya menyatakan urutan record, hasil tersebut belum membuktikan bahwa setiap pemicu ADC menghasilkan sampel. Dua belas rekaman utama dipakai untuk variasi usaha, sedangkan 24 rekaman lengkap dipakai untuk evaluasi respons digital. Gambar 4.2 memperlihatkan fitur sesi kontinu.

![](data:image/png;base64...)

Gambar 4.2 Perubahan nilai MAV dan RMS hasil pemrosesan selama sesi pengujian 10 menit.

Kenaikan dan penurunan kurva pada Gambar 4.2 mengikuti fase kontraksi dan relaksasi selama sesi 10 menit. Beberapa fase genggaman kuat menghasilkan puncak terbesar. Kurva fitur ini memperlihatkan perubahan amplitudo terhadap waktu, sedangkan pembatasan pita dinilai dari rekaman *raw* dengan metode pada Subbab 3.6.

## Hasil Penapisan Digital Butterworth

Perbandingan pada Tabel 4.2 menggunakan data setelah koreksi *offset* sebagai kondisi sebelum Butterworth dan keluaran HPF–LPF sebagai kondisi sesudahnya. Rata-rata MAV dan RMS merangkum perubahan amplitudo pada sesi kontinu, dengan satu data untuk setiap pembaruan fitur.

Tabel 4.2 Perbandingan nilai sebelum dan sesudah penapisan Butterworth.

| **Parameter** | **Sebelum Butterworth** | **Setelah Butterworth** | **Penurunan** |
| --- | --- | --- | --- |
| MAV rata-rata | 9,32 mV | 8,71 mV | 6,55% |
| RMS rata-rata | 12,67 mV | 11,25 mV | 11,24% |

Rata-rata MAV turun 6,55% dan RMS turun 11,24% setelah Butterworth. Persentase membandingkan rata-rata fitur sebelum dan sesudah tahap tersebut pada pembaruan yang sama. Angka ini menunjukkan perubahan amplitudo gabungan seluruh komponen. Identifikasi frekuensi yang dilemahkan menggunakan rekaman raw dan respons pada Tabel 4.3.

Untuk melihat perubahan bentuk sinyal, Gambar 4.3 mempertemukan sampel sebelum dan sesudah Butterworth pada indeks yang sama. Contoh yang digunakan ialah genggaman kuat pengulangan pertama.

![](data:image/png;base64...)

Gambar 4.3 Perbandingan sinyal tanpa tapis digital dan setelah penapisan Butterworth pada kondisi genggaman kuat.

Pada contoh genggaman kuat pertama, RMS turun dari 63,99 mV menjadi 62,56 mV atau 2,23% setelah Butterworth. Pada tiga rekaman relaks, penurunan relatif sebesar 14–17%, sedangkan pada tiga rekaman kuat sebesar 1,7–2,9%. Perbedaan ini menunjukkan proporsi amplitudo yang dilemahkan lebih besar pada rekaman relaks. Tanpa sinyal fisiologis acuan yang bebas gangguan, seluruh bagian yang dilemahkan tidak dapat disebut sebagai derau.

Evaluasi domain frekuensi membandingkan adc\_centered\_v dengan bandpass\_v pada 24 rekaman raw. Estimator H1 pada Persamaan 2.13 dan parameter spektral pada Subbab 3.6 menghasilkan respons eksperimen. Tabel 4.3 membandingkannya dengan respons koefisien HPF dan LPF pada frekuensi batas, pita lolos, dan pita redam.

Tabel 4.3 Perbandingan respons teoritis dan eksperimen kaskade Butterworth.

| **Frekuensi** | **Teoritis** | **Eksperimen rata-rata ± SD** |
| --- | --- | --- |
| 10 Hz | −12,31 dB | −12,22 ± 0,72 dB |
| 20 Hz | −3,01 dB | −3,02 ± 0,16 dB |
| 50 Hz | −0,11 dB | −0,10 ± 0,01 dB |
| 100 Hz | −0,01 dB | −0,01 ± 0,02 dB |
| 500 Hz | −3,01 dB | −3,01 ± 0,03 dB |
| 750 Hz | −8,90 dB | −8,91 ± 0,08 dB |
| 1000 Hz | −15,44 dB | −15,41 ± 0,23 dB |

Pada skala frekuensi nominal, respons eksperimen sebesar −3,02 ± 0,16 dB pada 20 Hz dan −3,01 ± 0,03 dB pada 500 Hz. Rata-ratanya mendekati acuan koefisien sekitar −3,01 dB. Simbol ± menyatakan standar deviasi antarekaman, bukan ketidakpastian kalibrasi frekuensi atau batas galat alat. Hasil mendukung kesesuaian respons digital pada rekaman. Penetapan batas dalam hertz aktual memerlukan pengukuran laju pencuplikan.

Tabel 4.3 menunjukkan respons mendekati acuan pada batas pita, pita lolos, dan pita redam. Pasangan antartahap memberi bukti kesesuaian transformasi digital dalam rekaman. Bukti tersebut melengkapi pemeriksaan struktur serta koefisien program. Identitas build yang menghasilkan rekaman tetap perlu dikaitkan dengan arsip versi pada Lampiran A.

## Hasil Tapis Takik 50 Hz

Butterworth masih meloloskan komponen sekitar 50 Hz sehingga takik ditambahkan untuk memberi pelemahan yang lebih selektif. Tabel 4.4 membandingkan fitur keluaran Butterworth dengan fitur setelah takik pada sesi kontinu.

Tabel 4.4 Perbandingan nilai sebelum dan sesudah tapis takik 50 Hz.

| **Parameter** | **Setelah Butterworth** | **Setelah tapis takik** | **Penurunan** |
| --- | --- | --- | --- |
| MAV rata-rata | 8,71 mV | 7,95 mV | 8,77% |
| RMS rata-rata | 11,25 mV | 10,45 mV | 7,10% |

Setelah takik, rata-rata MAV turun 8,77% dan RMS turun 7,10% terhadap keluaran Butterworth. Kedua persentase merangkum seluruh komponen sinyal dalam jendela fitur. Gambar 4.4 dan perhitungan PSD digunakan untuk meninjau bagian frekuensi yang berubah, sehingga penurunan amplitudo total tidak langsung ditafsirkan sebagai persentase derau yang hilang.

![](data:image/png;base64...)

Gambar 4.4 PSD sinyal sebelum dan sesudah tapis takik pada kondisi genggaman kuat.

Perbedaan spektrum pada Gambar 4.4 terutama tampak di sekitar 50 Hz. Komponen di luar daerah takik relatif tetap. Pelemahan dihitung pada frekuensi dominan yang teridentifikasi menggunakan Persamaan 2.19 dan pengaturan PSD pada Subbab 3.6.

Tiga POST\_RELAX\_RAW memperlihatkan komponen spektral menonjol pada kondisi relaks. Rekaman ini dipakai untuk mengamati pelemahan oleh takik, sebagaimana ditunjukkan pada Gambar 4.5. Gangguan tidak ditambahkan secara artifisial. Sumber fisik komponen tersebut tidak diidentifikasi melalui pengukuran terpisah, sehingga pembahasan mengacu pada puncak yang teramati dalam rekaman.

![](data:image/png;base64...)

Gambar 4.5 PSD sinyal pada kondisi interferensi listrik.

Pada tiga berkas POST\_RELAX\_RAW, puncak spektrum berada pada bin nominal 51 Hz dan 102 Hz. Setelah takik, rata-rata RMS berkurang 18,99% terhadap keluaran Butterworth. Pelemahan PSD pada 51 Hz sebesar 2,15 dB, 2,21 dB, dan 2,10 dB, dengan rata-rata 2,15 ± 0,05 dB. Nilai tersebut mendekati respons koefisien 2,33 dB pada frekuensi nominal yang sama. Perbandingan ini menilai kesesuaian respons, sedangkan komponen gangguan masih tersisa.

Pelemahan sekitar 2,15 dB pada bin 51 Hz menunjukkan bahwa komponen tersebut masih tersisa setelah takik. Kedekatan hasil dengan respons koefisien menjelaskan perilaku tapis pada frekuensi itu, tetapi tidak menyatakan bahwa gangguan telah ditekan sampai tingkat yang memadai bagi kendali. Penilaian kecukupan memerlukan kebutuhan masukan kendali yang terukur dan pengujian integrasi.

Pada bin 102 Hz, rasio PSD menghasilkan pelemahan sekitar 0,002 dB, setara perubahan daya sekitar 0,05%. Nilai ini secara praktis sangat kecil. Angka tersebut merupakan hasil perhitungan spektral, bukan ketelitian pengukuran yang telah dikalibrasi sampai lima angka desimal. Satu takik hanya menargetkan daerah sekitar 50 Hz dan belum menekan harmonik secara berarti. Pengujian tanpa stimulasi aktif juga belum menilai artefak FES.

Bin 51 Hz dan 102 Hz berasal dari spektrum dengan laju pencuplikan nominal 4.000 Hz dan jarak bin 1 Hz. Jendela Hann melebarkan puncak, sehingga jarak bin tidak identik dengan ketelitian frekuensi. Kedua posisi tersebut belum membuktikan pergeseran fisik jala-jala dari 50 Hz. Evaluasi yang dapat dipertahankan ialah besar pelemahan pada komponen rekaman tersebut.

## Hasil Ekstraksi Fitur RMS dan MAV

Setiap jendela 100 ms menghasilkan pasangan RMS dan MAV dari sinyal akhir. Tabel 4.5 memuat ukuran pemusatan, rentang, dan sebaran kedua fitur selama sesi kontinu.

Tabel 4.5 Statistik nilai MAV dan RMS hasil akhir pemrosesan.

| **Parameter** | **MAV** | **RMS** |
| --- | --- | --- |
| Rata-rata | 7,95 mV | 10,45 mV |
| Median | 4,12 mV | 4,84 mV |
| Minimum | 2,18 mV | 2,68 mV |
| Maksimum | 112,34 mV | 142,08 mV |
| Standar deviasi | 8,72 mV | 12,02 mV |

Tabel 4.5 menunjukkan median MAV 4,12 mV dan median RMS 4,84 mV pada sesi kontinu. Rentang kedua fitur lebar karena rekaman mencakup fase relaks dan beberapa tingkat usaha. Statistik ini merangkum amplitudo pada satu subjek dan tidak digunakan sebagai ukuran gaya atau akurasi fisiologis.

## Analisis Aktivitas Otot pada Variasi Genggaman

Tabel 4.6 membandingkan RMS keluaran takik pada empat kelompok arsip. Setiap nilai pengulangan dihitung dari 8.000 sampel, kemudian tiga nilai diringkas menjadi rata-rata, standar deviasi, dan CV. Sedang RPE 5 merupakan nama operasional kelompok MEDIUM\_RPE5 sesuai Subbab 3.6. Kelompok tidak menyatakan tingkat gaya terkalibrasi atau kategori Borg yang berjarak sama.

Tabel 4.6 Nilai RMS pada variasi aktivitas otot.

| **Kondisi** | **Pengulangan 1 (mV)** | **Pengulangan 2 (mV)** | **Pengulangan 3 (mV)** | **Rata-rata ± SD (mV)** | **CV (%)** |
| --- | --- | --- | --- | --- | --- |
| Relaks | 6,99 | 7,99 | 7,93 | 7,64 ± 0,56 | 7,3 |
| Ringan | 20,45 | 12,74 | 15,12 | 16,10 ± 3,95 | 24,5 |
| Sedang RPE 5 | 37,53 | 36,82 | 41,22 | 38,52 ± 2,36 | 6,1 |
| Kuat | 61,85 | 35,11 | 61,17 | 52,71 ± 15,25 | 28,9 |

Ringkasan Tabel 4.6 memperlihatkan kenaikan rata-rata RMS dari 7,64 mV saat relaks menjadi 16,10 mV pada ringan, 38,52 mV pada sedang RPE 5, dan 52,71 mV pada kuat. Gambar 4.6 menempatkan keempat rata-rata tersebut dalam satu perbandingan. Urutan kenaikan berlaku pada rata-rata dan tidak selalu muncul pada setiap pengulangan.

![](data:image/png;base64...)

Gambar 4.6 Perbandingan nilai RMS pada variasi aktivitas otot.

CV kelompok sedang RPE 5 sebesar 6,1%, sedangkan ringan 24,5% dan kuat 28,9%. CV tersebut merangkum sebaran tiga nilai terhadap rata-rata masing-masing. Nilai yang lebih kecil menunjukkan variasi relatif lebih rendah pada rekaman itu. Hasil belum memisahkan pengaruh perubahan usaha, posisi, kontak sensor, dan riwayat kontraksi.

Pada kategori kuat, pengulangan kedua menghasilkan 35,11 mV. Nilai ini berada di bawah seluruh pengulangan sedang, yaitu 36,82–41,22 mV, sedangkan dua pengulangan kuat lainnya mencapai 61,85 mV dan 61,17 mV. Urutan kategori usaha karena itu tidak konsisten pada setiap pengulangan. Data tetap disertakan karena tidak ada bukti teknis yang membenarkan penghapusannya.

Keempat rata-rata meningkat sesuai urutan nama kelompok pada arsip, tetapi pengulangan yang tumpang tindih membatasi penafsirannya. Data mendukung adanya perubahan amplitudo antarkondisi pengujian. Hasil ini belum menetapkan hubungan monoton EMG terhadap gaya atau ambang pemisah yang berlaku untuk setiap pengulangan.

## Analisis Konsistensi Aktivitas EMG pada Fase Perubahan Posisi Tangan

Analisis memakai tiga jendela pada fase perubahan posisi tangan, yaitu 496 ≤ t < 506 detik, 531 ≤ t < 541 detik, dan 557 ≤ t < 567 detik. Waktu t mengacu pada awal sesi kontinu. Setiap jendela memuat 98 pembaruan fitur unik. Tabel 4.7 menyajikan rata-rata MAV dan RMS tiap jendela serta variasi antartiga rata-rata tersebut.

Tabel 4.7 Nilai MAV dan RMS pada fase perubahan posisi tangan.

| **Jendela** | **Interval (s)** | **MAV terfilter (mV)** | **RMS terfilter (mV)** |
| --- | --- | --- | --- |
| 1 | 496–506 | 27,65 | 39,61 |
| 2 | 531–541 | 27,45 | 37,92 |
| 3 | 557–567 | 27,97 | 38,00 |
| Rata-rata | – | 27,69 | 38,51 |
| Standar deviasi | – | 0,26 | 0,95 |

Rata-rata MAV tiap jendela berada pada 27,45–27,97 mV, sedangkan RMS pada 37,92–39,61 mV. Ringkasan antartiga rata-rata menghasilkan MAV 27,69 ± 0,26 mV dan RMS 38,51 ± 0,95 mV, dengan CV 0,95% dan 2,47%. Nilai tersebut menjelaskan kedekatan rata-rata antarsegmen terpilih. Fluktuasi di dalam setiap segmen tidak dirangkum oleh CV antarrata-rata ini. Gambar 4.7 membandingkan ketiga jendela.

![](data:image/png;base64...)

Gambar 4.7 Perbandingan rata-rata MAV dan RMS pada tiga jendela fase perubahan posisi tangan.

Ketiga jendela dipilih pada bagian dengan amplitudo relatif stabil. Hasil berlaku pada segmen tersebut dan tidak mencakup seluruh transisi gerak. Istilah sudut pada grafik mengacu pada fase perubahan posisi, tanpa pasangan data IMU yang sinkron. Analisis ini menjadi pengamatan deskriptif amplitudo dan tidak menjadi validasi terhadap sudut atau penolakan artefak gerakan.

## Hasil Telemetri UART dan Pengolahan Data pada GUI

Berkas EMG\_GUI\_2026-08-05\_15-25-34\_483.csv memuat 1.420 baris penerimaan dengan protokol EMG\_RMS\_MV. Kolom sequence pada berkas bernilai 95–1.514. Raw\_line hanya berisi penanda protokol dan nilai RMS, sehingga nomor pada log tidak dapat diperlakukan sebagai pencacah pengiriman STM32. Tabel 4.8 merangkum pemeriksaan penerimaan.

Tabel 4.8 Hasil pengujian telemetri UART dan penerimaan data pada GUI.

| **Parameter** | **Hasil** |
| --- | --- |
| Protokol data | EMG\_RMS\_MV |
| Jumlah data diterima | 1.420 data |
| Rentang sequence pada log | 95–1.514 |
| Celah sequence pada log | 0, bukan ukuran kehilangan paket pemancar |
| Interval pencatatan log median | 0,098 s |
| Payload berbeda dari kolom RMS | 0 data |
| Interval pencatatan log rata-rata | 0,10214 s |
| Rentang interval pencatatan log | 0,096–0,116 s |
| Tingkat kehilangan paket pemancar | Belum dapat ditentukan dari log ini |

Sebanyak 1.420 baris menghasilkan 1.419 selang pencatatan, dengan median 0,098 detik, rata-rata 0,10214 detik, dan rentang 0,096–0,116 detik. Nilai pada raw\_line cocok dengan filtered\_rms\_mv pada seluruh baris yang tersimpan. Selang ini meliputi penerimaan dan penulisan log di komputer. Sebarannya bukan ukuran jitter pemicu ADC. Tanpa cap waktu bersama pada masukan sensor dan GUI, log juga tidak memberikan latensi ujung ke ujung.

Gambar 4.8 mempertemukan RMS yang diterima dengan hasil penghalusan EMA pada sumbu waktu yang sama. Perbandingan ini digunakan untuk meninjau perubahan tampilan setelah penghalusan.

![](data:image/png;base64...)

Gambar 4.8 Perbandingan nilai RMS yang diterima dan hasil penghalusan EMA pada GUI.

Gambar 4.8 memperlihatkan EMA mengikuti RMS secara lebih bertahap. Pada 58,91 detik, nilai RMS 107,86 mV disertai EMA 72,91 mV. Selisih tersebut merupakan contoh respons penghalusan yang tersimpan pada GUI. Perataan tampilan tidak menambah bukti ketepatan fitur terhadap aktivitas fisiologis dan tidak digunakan untuk menghitung latensi kendali.

Log mendukung penerimaan dan konsistensi RMS pada sesi tercatat. Pengukuran kehilangan paket memerlukan pencacah pemancar dan pembanding jumlah pengiriman. Log tidak mengukur data yang gagal diparsing sebelum dicatat. Hasil menjawab evaluasi antarmuka pada Subbab 1.3. Validasi kendali memerlukan pengujian terpisah.

## Evaluasi Keseluruhan Subsistem Pemrosesan Sinyal EMG

Kesesuaian respons dengan koefisien dan keterulangan perhitungan menjadi bukti utama tahap digital. Fitur serta log UART menunjukkan keluaran antarmuka pada sesi uji. Pelemahan pada 51 Hz masih terbatas dan kategori usaha belum terpisah konsisten. Tabel 4.9 merangkum hasil sesuai batas pembuktiannya.

Tabel 4.9 Ketercapaian tujuan penelitian berdasarkan hasil pengujian.

| **Tujuan penelitian** | **Bukti hasil pengujian** | **Penilaian ketercapaian** |
| --- | --- | --- |
| Implementasi subsistem | Konfigurasi 4.000 Hz, HPF 20 Hz, LPF 500 Hz, takik 50 Hz/Q = 30. Fitur per 400 sampel. Tercatat 5.901 nomor pembaruan tanpa celah dan flag kesalahan serta clipping bernilai nol. | Operasi pemrosesan teramati pada sesi uji. Ketepatan waktu dan identitas build pengujian memerlukan pembuktian tersendiri. |
| Pembatasan pita Butterworth | *Gain* −3,02 ± 0,16 dB pada 20 Hz dan −3,01 ± 0,03 dB pada 500 Hz. Selisih rerata dari acuan −3,01 dB sekitar 0,01 dB dan 0,00 dB pada ketelitian pelaporan. | Evaluasi menunjukkan respons mendekati rancangan. Selisih dilaporkan tanpa menetapkan ambang galat kelulusan setelah pengujian. |
| Pelemahan takik | Pelemahan 51 Hz sebesar 2,15 ± 0,05 dB. Pelemahan 102 Hz sekitar 0,002 dB pada hasil perhitungan PSD. | Besar pelemahan terukur pada rekaman. Komponen sekitar 51 Hz masih tersisa dan harmonik 102 Hz berubah sangat kecil. |
| Fitur aktivitas | RMS kelompok relaks 7,64 mV, ringan 16,10 mV, sedang RPE 5 38,52 mV, dan kuat 52,71 mV. | Perubahan amplitudo teramati sesuai kelompok arsip. Hasil belum menetapkan urutan gaya atau pemisahan kategori yang konsisten. |
| Penerimaan UART | 1.420 nilai RMS konsisten dengan raw\_line. Median interval pencatatan 0,098 s. | Penerimaan dan konsistensi parsing teramati. Kelengkapan semua paket pemancar serta latensi ujung ke ujung belum dinilai. |

# BAB V PENUTUP

## Kesimpulan

Pengujian menghasilkan tiga kesimpulan sesuai tujuan penelitian.

1. Subsistem menerapkan akuisisi pada konfigurasi nominal 4.000 Hz, Butterworth lolos tinggi 20 Hz, lolos rendah 500 Hz, serta takik 50 Hz dengan Q = 30 pada STM32F411CEU6. RMS dan MAV diperbarui setiap 400 sampel. Sesi 602,10 detik memuat 5.901 nomor pembaruan fitur tanpa celah, dengan flag kesalahan dan clipping bernilai nol pada log. Hasil mendukung operasi sesi uji. Ketepatan waktu dan identitas build memerlukan pembuktian tersendiri.
2. Pada 24 rekaman raw, respons Butterworth sebesar −3,02 ± 0,16 dB pada 20 Hz dan −3,01 ± 0,03 dB pada 500 Hz menurut skala pencuplikan nominal, mendekati acuan koefisien sekitar −3,01 dB. Rata-rata MAV dan RMS sesi kontinu turun 6,55% dan 11,24% setelah Butterworth. Pada tiga rekaman interferensi, takik melemahkan komponen bin 51 Hz sebesar 2,15 ± 0,05 dB dan memberi perubahan sekitar 0,002 dB pada 102 Hz. Hasil menunjukkan kesesuaian respons serta batas selektivitas tapis. Perubahan fitur tidak menyatakan persentase derau yang berhasil dipisahkan.
3. Rata-rata RMS kelompok relaks, ringan, sedang RPE 5, dan kuat masing-masing sebesar 7,64 mV, 16,10 mV, 38,52 mV, dan 52,71 mV. Kelompok mengikuti label arsip dan menunjukkan perubahan amplitudo pada satu subjek, dengan urutan yang tidak konsisten pada setiap pengulangan. Sebanyak 1.420 nilai RMS pada log GUI sesuai dengan raw\_line, dengan median interval pencatatan 0,098 detik. Hasil mendukung penyediaan fitur dan konsistensi antarmuka data. Penelitian belum menetapkan hubungan gaya, kelengkapan paket pemancar, atau kinerja selama FES aktif.

## Saran

Saran berikut menindaklanjuti keterbatasan pengukuran dan pengujian pada penelitian ini.

1. Penelitian lanjutan dapat memakai protokol yang mencatat lokasi sensor terhadap penanda anatomi, urutan kondisi, instruksi usaha, dan durasi jeda. Tambahan subjek dan pembanding gaya akan membantu menilai keterulangan serta hubungan EMG dengan gaya.
2. Perbandingan beberapa nilai Q dan metode takik dapat memakai ukuran sisa interferensi serta perubahan sEMG pada pita yang dipertahankan. Kriteria penilaian perlu ditetapkan sebelum pengujian, termasuk kebutuhan masukan kendali bila subsistem diintegrasikan.
3. Perekaman EMG dan IMU yang sinkron dapat menunjukkan perubahan amplitudo selama gerakan. Penetapan segmen sebelum analisis akan membantu menilai fase transisi secara konsisten.
4. Pengukuran frekuensi pencuplikan aktual dan jitter memerlukan acuan waktu independen pada pemicu ADC. Pengukuran latensi memerlukan cap waktu bersama dari masukan sensor sampai tampilan GUI. Pencacah pengiriman dan log penerimaan dapat membantu menilai kehilangan data. Pencatatan versi firmware, GUI, dan konfigurasi akan memudahkan reproduksi hasil.
5. Pengujian bersama FES aktif masih diperlukan untuk menilai artefak stimulasi pada jalur EMG. Prosedur keselamatan dan kriteria penerimaan harus ditetapkan sebelum pengujian tersebut.

# DAFTAR PUSTAKA

[1] *World Health Organization*, “*Stroke,*” *World Health Organization*, 2025. https://www.who.int/news-room/fact-sheets/detail/*stroke*. Diakses 14 September 2026.

[2] GBD 2021 *Stroke* Risk Factor Collaborators, “*Global, regional, and national burden of stroke and its risk factors, 1990–2021: a systematic analysis for the Global Burden of Disease Study 2021,*” *The Lancet Neurology*, vol. 23, no. 10, pp. 973–1003, 2024, doi: 10.1016/S1474-4422(24)00369-7.

[3] M. A. Khan, H. Fares, H. Ghayvat, I. C. Brunner, S. Puthusserypady, B. Razavi, M. Lansberg, A. Poon, *and* K. J. Meador, “*A systematic review on functional electrical stimulation based rehabilitation systems for upper limb post-stroke recovery,*” *Frontiers in Neurology*, vol. 14, *Art. no.* 1272992, 2023, doi: 10.3389/fneur.2023.1272992.

[4] F. Rossi, P. Motto Ros, R. M. Rosales, *and* D. Demarchi, “*Embedded Bio-Mimetic System for Functional Electrical Stimulation Controlled by Event-Driven sEMG,*” *Sensors*, vol. 20, no. 5, *Art. no.* 1535, 2020, doi: 10.3390/s20051535.

[5] K. Li, J. Zhang, L. Wang, M. Zhang, J. Li, *and* S. Bao, “*A review of the key technologies for sEMG-based human-robot interaction systems,*” *Biomedical Signal Processing and Control*, vol. 62, *Art. no.* 102074, 2020, doi: 10.1016/j.bspc.2020.102074.

[6] F. Mandrile, D. Farina, M. Pozzo, *and* R. Merletti, “*Stimulation artifact in surface EMG signal: effect of the stimulation waveform, detection system, and current amplitude using hybrid stimulation technique,*” *IEEE Transactions on Neural Systems and Rehabilitation Engineering*, vol. 11, no. 4, pp. 407–415, 2003, doi: 10.1109/TNSRE.2003.819791.

[7] T. Roland, S. Amsuess, M. F. Russold, *and* W. Baumgartner, “*Ultra-Low-Power Digital Filtering for Insulated EMG Sensing,*” *Sensors*, vol. 19, no. 4, *Art. no.* 959, 2019, doi: 10.3390/s19040959.

[8] A. V. Oppenheim *and* R. W. Schafer, *Discrete-Time Signal Processing*, *3rd ed.* Upper Saddle River, NJ, USA: Pearson, 2010.

[9] J. G. Proakis *and* D. G. Manolakis, *Digital Signal Processing: Principles, Algorithms, and Applications*, *4th ed.* Upper Saddle River, NJ, USA: Pearson, 2007.

[10] L. McManus, G. De Vito, *and* M. M. Lowery, “*Analysis and Biophysics of Surface EMG for Physiotherapists and Kinesiologists: Toward a Common Language With Rehabilitation Engineers,*” *Frontiers in Neurology*, vol. 11, *Art. no.* 576729, 2020, doi: 10.3389/fneur.2020.576729.

[11] C. J. De Luca, A. Adam, R. Wotiz, L. D. Gilmore, *and* S. H. Nawab, “*Decomposition of surface EMG signals,*” *Journal of Neurophysiology*, vol. 96, no. 3, pp. 1646–1657, 2006, doi: 10.1152/jn.00009.2006.

[12] H. J. Hermens, B. Freriks, C. Disselhorst-Klug, *and* G. Rau, “*Development of recommendations for SEMG sensors and sensor placement procedures,*” *Journal of Electromyography and Kinesiology*, vol. 10, no. 5, pp. 361–374, 2000, doi: 10.1016/S1050-6411(00)00027-4.

[13] D. Staudenmann, K. Roeleveld, D. F. Stegeman, *and* J. H. van Dieën, “*Methodological aspects of SEMG recordings for force estimation—A tutorial and review,*” *Journal of Electromyography and Kinesiology*, vol. 20, no. 3, pp. 375–387, 2010, doi: 10.1016/j.jelekin.2009.08.005.

[14] DFRobot, “*Gravity: Analog EMG Sensor by OYMotion (SEN0240),*” *DFRobot Wiki/Product Documentation*. https://wiki.dfrobot.com/SEN0240. Diakses 14 September 2026.

[15] STMicroelectronics, “*STM32F411xC STM32F411xE Arm Cortex-M4 32b MCU+FPU, 125 DMIPS, 512 KB Flash, 128 KB RAM, USB OTG FS, 11 TIMs, 1 ADC, 13 communication interfaces,*” *Datasheet* DS10314 Rev. 8, *Jan.* 2024. https://www.st.com/resource/en/*datasheet*/stm32f411ce.pdf.

[16] S. Butterworth, “*On the theory of filter amplifiers,*” *Experimental Wireless and the Wireless Engineer*, vol. 7, pp. 536–541, *Oct.* 1930.

[17] G. Borg, *Borg's Perceived Exertion and Pain Scales*. Champaign, IL, USA: Human Kinetics, 1998.

[18] J. S. Bendat *and* A. G. Piersol, *Random Data: Analysis and Measurement Procedures*, *4th ed.* Hoboken, NJ, USA: Wiley, 2010, doi: 10.1002/9781118032428.

[19] P. D. Welch, “*The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms,*” *IEEE Transactions on Audio and Electroacoustics*, vol. AU-15, no. 2, pp. 70–73, 1967, doi: 10.1109/TAU.1967.1161901.

[20] *The SciPy community*, “*scipy.signal.butter,*” *SciPy API Reference*. [*Online*]. https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html

[21] *The SciPy community*, “*scipy.signal.iirnotch,*” *SciPy API Reference and filter design implementation*. https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.iirnotch.html. Diakses 14 September 2026.

[22] W3C, “*Audio EQ Cookbook,*” *W3C Group Note*, 8-*Jun*-2021. https://www.w3.org/TR/audio-eq-cookbook/. Diakses 14 September 2026.

[23] BorgPerception, “Borg CR scale (CR10) English Instruction.” https://borgperception.se/cr10stinstr/. Diakses 15 September 2026.

# BIODATA PENULIS

|  |  |
| --- | --- |
| ![](data:image/png;base64...) | Nama Lengkap : Ardhya Novri Ramadhan  NIM : 21060122130096  Tempat, Tanggal Lahir : Jakarta, 02 November 2004  Jenis Kelamin : Laki-laki  Alamat : Jl. Gamprit 1 GG Mangga 3 No. 48A, Jatiwaringin, Pondok Gede, Kota Bekasi  Jurusan : S-1 Teknik Elektro  Nomor Telepon : 081291552970  *E-mail* : ardhyasan@gmail.com  Konsentrasi : Elektronika  IP Kumulatif : 3,41 |

**Pengalaman dan Prestasi yang pernah diraih:**

1. Magang Mandiri di PT Angkasa Pura Indonesia

2. *Google Student Ambassador* 2025

3. Kerja Praktik di CV REDESMA INDONESIA

|  |  |
| --- | --- |
|  | Semarang, 23 Agustus 2026    Ardhya Novri Ramadhan  21060122130096 |

# LAMPIRAN A SENARAI PROGRAM STM32

Senarai program pada tautan berikut menjadi rujukan lampiran. Pemetaan berkas dan batas kesesuaian versi dijelaskan setelah kode QR.

https://qr-codes.io/FPFupo

atau pindaikode QR di bawah ini.

![](data:image/png;base64...)

**Identitas berkas program**

Berkas Core/Src/emg\_app.c memuat tiga biquad Direct Form II Transposed, koefisien pada Tabel 3.8 dan 3.10, serta pembaruan fitur 400 sampel. Core/Inc/emg\_app.h memuat deklarasi antarmuka. Core/Src/main.c dan TEST2.ioc digunakan untuk menelusuri konfigurasi perangkat dan integrasi.

Salinan program yang diperiksa pada 14 September 2026 menggunakan telemetri integrasi yang berbeda dari raw\_line EMG\_RMS\_MV pada log tanggal 5 Agustus 2026. Kesamaan koefisien dan algoritma tidak membuktikan bahwa salinan tersebut merupakan build yang dipakai pada seluruh sesi uji. Identitas build pengujian, termasuk sumber dan konfigurasi saat perekaman, perlu ditautkan secara terpisah.

Paket\_Bukti\_Audit\_Ardhya.zip menyertakan snapshot program saat audit dengan nama folder firmware\_saat\_audit. Manifest SHA-256 menandai identitas berkas tersebut. Snapshot ini berfungsi sebagai pembanding kode, bukan pengganti arsip firmware pengujian.

# LAMPIRAN B DATA PENGUJIAN

Data pengujian pada tautan berikut menjadi rujukan lampiran. Daftar kelompok berkas dan cara menghitung hasil tersedia pada halaman berikutnya.

https://qr.generatorqr.com/8Fndqzi2h

atau pindaikode QR di bawah ini.

![](data:image/png;base64...)

**Peta data pengujian**

Paket\_Bukti\_Audit\_Ardhya.zip menyertakan data lokal yang digunakan dalam audit. Tabel B.1 merangkum kelompok rekaman. Seluruh 24 rekaman lengkap digunakan untuk respons Butterworth. Pengelompokan usaha tetap mengikuti label pada arsip dan tidak menyatakan seleksi acak atau protokol yang ditetapkan sebelum perekaman.

Tabel B.1 Pemetaan berkas terhadap analisis

| **Berkas atau kelompok** | **Jumlah** | **Penggunaan** |
| --- | --- | --- |
| EMG\_10\_Menit\_Ardhya\_2026-07-28.xlsx | 1 workbook | Statistik fitur, Tabel 4.1, 4.2, 4.4, 4.5, dan 4.7 |
| RELAX\_RAW\_01–03 | 3 | Kelompok relaks, Tabel 4.6 |
| LIGHT\_RAW\_01–03 | 3 | Kelompok ringan, Tabel 4.6 |
| MEDIUM\_RPE5\_RAW\_01–03 | 3 | Kelompok sedang RPE 5, Tabel 4.6 |
| STRONG\_RAW\_01–03 | 3 | Kelompok kuat, Tabel 4.6 |
| MEDIUM\_RAW\_01–03 | 3 | Pengulangan teknis, hanya evaluasi transfer |
| MEDIUM\_RAW\_01\_RETRY, MEDIUM\_RAW\_02\_RETRY, MEDIUM\_RAW\_03\_RETRY | 3 | Pengulangan teknis, hanya evaluasi transfer |
| POST\_RELAX\_RAW\_01–03 | 3 | Contoh interferensi, Subbab 4.4 |
| CLEAN\_REST\_CHECK, POST\_RELAX\_CLEAN\_01–02 | 3 | Pemeriksaan relaks, evaluasi transfer |
| EMG\_GUI\_2026-08-05\_15-25-34\_483.csv | 1 log | Penerimaan UART, Tabel 4.8 |
| REST\_TEST\_01.bin | 0 record | Berkas kosong, tidak masuk 24 rekaman |

Setiap kelompok raw memuat biner, CSV, dan metadata JSON. Tabel mempertahankan kelompok tanpa label RPE 5 serta kelompok pengulangan agar cakupan analisis terlihat. Sedang RPE 5 merupakan nama arsip, dengan penafsiran skala dijelaskan pada Subbab 3.6. Perubahan instruksi antarkelompok belum terdokumentasi sebagai protokol sebelum pengujian.

Validasi memeriksa 8.000 record, kesesuaian biner dengan CSV, CRC-32, dan SHA-256. Hasil tidak menggantikan pengukuran waktu atau penelusuran build firmware. Paket bukti memuat skrip hitung ulang, hasil numerik, dan manifest berkas.