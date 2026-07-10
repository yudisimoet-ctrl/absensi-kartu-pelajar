-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Waktu pembuatan: 09 Okt 2025 pada 17.08
-- Versi server: 10.3.39-MariaDB-cll-lve
-- Versi PHP: 8.4.11

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `fyxhpdmx_537`
--

-- --------------------------------------------------------

--
-- Struktur dari tabel `absensi`
--

CREATE TABLE `absensi` (
  `id` int(11) NOT NULL,
  `siswa_id` int(11) DEFAULT NULL,
  `tanggal` date DEFAULT NULL,
  `jam` time DEFAULT NULL,
  `jam_pulang` time DEFAULT NULL,
  `jam_dzuhur` time DEFAULT NULL,
  `status` enum('H','S','I','A') DEFAULT 'H',
  `keterangan` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `absensi`
--

INSERT INTO `absensi` (`id`, `siswa_id`, `tanggal`, `jam`, `jam_pulang`, `jam_dzuhur`, `status`, `keterangan`) VALUES
(1, 1, '2025-10-09', '16:44:03', '16:44:31', NULL, 'H', NULL);

-- --------------------------------------------------------

--
-- Struktur dari tabel `hari_libur`
--

CREATE TABLE `hari_libur` (
  `id` int(11) NOT NULL,
  `tanggal` date DEFAULT NULL,
  `deskripsi` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `jurnal_kebiasaan`
--

CREATE TABLE `jurnal_kebiasaan` (
  `id` int(11) NOT NULL COMMENT 'Primary Key, Auto Increment',
  `siswa_id` int(11) NOT NULL COMMENT 'Relasi ke tabel siswa',
  `jam_bangun` time NOT NULL COMMENT 'Jam bangun tidur',
  `beribadah` enum('Di Rumah','Di Tempat Ibadah') NOT NULL COMMENT 'Tempat beribadah',
  `jam_olahraga` time DEFAULT NULL COMMENT 'Jam melakukan olahraga',
  `makanan_sehat` enum('Makanan Asli','Makanan Instan/Pabrik') NOT NULL COMMENT 'Jenis makanan sehat',
  `jam_belajar` time DEFAULT NULL COMMENT 'Jam belajar',
  `bermasyarakat` text DEFAULT NULL COMMENT 'Aktivitas bermasyarakat',
  `jam_tidur` time DEFAULT NULL COMMENT 'Jam tidur',
  `keterangan` text DEFAULT NULL COMMENT 'Catatan tambahan',
  `foto` varchar(255) DEFAULT NULL COMMENT 'Foto dokumentasi',
  `tanggal_input` timestamp NOT NULL DEFAULT current_timestamp() COMMENT 'Tanggal input data'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `jurnal_kebiasaan`
--

INSERT INTO `jurnal_kebiasaan` (`id`, `siswa_id`, `jam_bangun`, `beribadah`, `jam_olahraga`, `makanan_sehat`, `jam_belajar`, `bermasyarakat`, `jam_tidur`, `keterangan`, `foto`, `tanggal_input`) VALUES
(1, 2, '20:28:00', 'Di Tempat Ibadah', '00:00:00', 'Makanan Instan/Pabrik', '00:00:00', '', '00:00:00', '', NULL, '2025-09-04 13:27:51'),
(2, 1, '20:45:00', 'Di Rumah', '00:00:00', 'Makanan Instan/Pabrik', '00:00:00', '', '00:00:00', '', NULL, '2025-09-04 13:44:40'),
(3, 1, '20:45:00', 'Di Rumah', '00:00:00', 'Makanan Asli', '00:00:00', '', '00:00:00', '', '1756993497_Pp.jpg', '2025-09-04 13:44:57'),
(4, 1, '05:00:00', '', '16:58:00', '', '00:00:00', '', '00:00:00', '', NULL, '2025-10-09 09:57:45');

-- --------------------------------------------------------

--
-- Struktur dari tabel `pelanggaran`
--

CREATE TABLE `pelanggaran` (
  `id` int(11) NOT NULL,
  `nama_pelanggaran` varchar(100) NOT NULL,
  `poin` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `pelanggaran`
--

INSERT INTO `pelanggaran` (`id`, `nama_pelanggaran`, `poin`) VALUES
(1, 'Terlambat masuk sekolah', 5),
(2, 'Tidak memakai seragam rapi', 5),
(3, 'Tidak membawa buku pelajaran', 3),
(4, 'Membolos tanpa izin', 20),
(5, 'Merokok di lingkungan sekolah', 50),
(6, 'Berkelahi di sekolah', 75),
(7, 'Menggunakan HP saat pelajaran', 15),
(8, 'Tidak mengikuti upacara', 10),
(9, 'Mengotori lingkungan sekolah', 10),
(10, 'Bersikap tidak sopan pada guru', 30);

-- --------------------------------------------------------

--
-- Struktur dari tabel `pelanggaran_log`
--

CREATE TABLE `pelanggaran_log` (
  `id` int(11) NOT NULL,
  `siswa_id` int(11) NOT NULL,
  `pelanggaran_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `keterangan` text DEFAULT NULL,
  `tanggal` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `pelanggaran_log`
--

INSERT INTO `pelanggaran_log` (`id`, `siswa_id`, `pelanggaran_id`, `user_id`, `keterangan`, `tanggal`) VALUES
(1, 1, 5, 262, '', '2025-10-09 09:52:03');

-- --------------------------------------------------------

--
-- Struktur dari tabel `profil_sekolah`
--

CREATE TABLE `profil_sekolah` (
  `id` int(11) NOT NULL,
  `nama_sekolah` varchar(200) NOT NULL,
  `alamat` text NOT NULL,
  `kepala_sekolah` varchar(200) NOT NULL,
  `nip_kepala` varchar(50) NOT NULL,
  `logo` varchar(255) DEFAULT NULL,
  `background_kartu` varchar(255) DEFAULT NULL,
  `key_wa_sidobe` varchar(200) NOT NULL,
  `jam_masuk` time DEFAULT NULL,
  `jam_pulang` time DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `profil_sekolah`
--

INSERT INTO `profil_sekolah` (`id`, `nama_sekolah`, `alamat`, `kepala_sekolah`, `nip_kepala`, `logo`, `background_kartu`, `key_wa_sidobe`, `jam_masuk`, `jam_pulang`) VALUES
(1, 'SD AL-IHSAN', 'Jalan Kebagusan 99, Sumberberkah, Kec. Gerahripah', 'Nir Singgih, S.Pd.SD.', '198901 202321 1 003', 'logo_1755998407.png', 'background_1760001608.jpg', 'YKtUbQCrtMCscqmJdAqwwWrvejEUnjMHHeJkMXuRFcBVLGxMGR', '07:00:00', '13:00:00');

-- --------------------------------------------------------

--
-- Struktur dari tabel `siswa`
--

CREATE TABLE `siswa` (
  `id` int(11) NOT NULL,
  `nis` varchar(20) DEFAULT NULL,
  `nisn` varchar(20) DEFAULT NULL,
  `nama` varchar(100) DEFAULT NULL,
  `kelas` varchar(50) DEFAULT NULL,
  `status` varchar(10) NOT NULL DEFAULT 'aktif',
  `no_wa` varchar(20) DEFAULT NULL,
  `rfid_uid` varchar(50) DEFAULT NULL,
  `foto_siswa` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `siswa`
--

INSERT INTO `siswa` (`id`, `nis`, `nisn`, `nama`, `kelas`, `status`, `no_wa`, `rfid_uid`, `foto_siswa`) VALUES
(1, '4444', '1010101010', 'Nama Siswa 1', '7A', 'aktif', '6281578049508', NULL, 'siswa_1_1760002920.jpg');

-- --------------------------------------------------------

--
-- Struktur dari tabel `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `nama` varchar(100) DEFAULT NULL,
  `role` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `nama`, `role`) VALUES
(1, 'admin', '0192023a7bbd73250516f069df18b500', NULL, 'admin'),
(2, 'wali', 'bf8cd26e6c6732b8df17a31b54800ed8', NULL, 'wali'),
(3, 'guru', '77e69c137812518e359196bb2f5e9bb9', 'guru', 'guru'),
(161, '1010101010', '3fd5c2a0df1ce9dc01f0698adc57c72b', 'Nama Siswa 1', 'siswa'),
(162, '1010101011', '7ea61fd1aab64ab975b12d51eceb300e', 'Nama Siswa 2', 'siswa'),
(163, '1010101012', '8cdbb06670ce399057e3e49dafd81cc2', 'Nama Siswa 3', 'siswa'),
(164, '1010101013', '18b1199437624ebb275467290dbb8c63', 'Nama Siswa 4', 'siswa'),
(165, '1010101014', '917b99f8c38154b7643a91b5931087b7', 'Nama Siswa 5', 'siswa'),
(166, '1010101015', '16cbeb57c916d04c9dbae1b58504e021', 'Nama Siswa 6', 'siswa'),
(167, '1010101016', 'e1893fa5569ed4e7fee78217bd2ffb6f', 'Nama Siswa 7', 'siswa'),
(168, '1010101017', '97678c93c88875790982030a3c9ea1f7', 'Nama Siswa 8', 'siswa'),
(169, '1010101018', 'eb6b22945d380a9fe4b30908d467efa1', 'Nama Siswa 9', 'siswa'),
(171, '1010101020', '672a7c397ce5701958d5cf0f76c04854', 'Nama Siswa 11', 'siswa'),
(172, '1010101021', '4e132cd80beef025f1bfa41eac3ad5b5', 'Nama Siswa 12', 'siswa'),
(173, '1010101022', '742aa04646a9cf667203e526b7034218', 'Nama Siswa 13', 'siswa'),
(174, '1010101023', '5dc5dd1686be523b14fe0204708f3252', 'Nama Siswa 14', 'siswa'),
(175, '1010101024', 'c41718c90a29734a436daaed03d1237f', 'Nama Siswa 15', 'siswa'),
(176, '1010101025', '1035c7978209903ecb3cd8a9eb981452', 'Nama Siswa 16', 'siswa'),
(177, '1010101026', '97b1b993c55bdf588bd6882778ee74fa', 'Nama Siswa 17', 'siswa'),
(178, '1010101027', 'f7e7ec35b77982f98b280cee33b04792', 'Nama Siswa 18', 'siswa'),
(179, '1010101028', '8716bc2552da3744724ba8aa8bb6a7ba', 'Nama Siswa 19', 'siswa'),
(180, '1010101029', '557d8e6f75affd31a084dfc2a0d44f36', 'Nama Siswa 20', 'siswa'),
(181, '1010101030', '64955d49f852b3d93a18c1de95514391', 'Nama Siswa 21', 'siswa'),
(182, '1010101031', '87c8751f8c460c613afc2366bf2b6e1e', 'Nama Siswa 22', 'siswa'),
(183, '1010101032', '17f201a1302d45c6bc8a1eab8f57b445', 'Nama Siswa 23', 'siswa'),
(184, '1010101033', '2c014da41d32992707da7883ad2e2d5d', 'Nama Siswa 24', 'siswa'),
(185, '1010101034', 'e6682d9f163c013d443e3e1423e5458a', 'Nama Siswa 25', 'siswa'),
(186, '1010101035', '6731c6e4cec9844192be4e35e967e87e', 'Nama Siswa 26', 'siswa'),
(187, '1010101036', '3b5bedfb3f75524d6c05df65b2ceba7e', 'Nama Siswa 27', 'siswa'),
(188, '1010101037', '9e306ef4ab467216ecb29d2566827b1d', 'Nama Siswa 28', 'siswa'),
(189, '1010101038', '131517185716b0f3c72cfcfa69cf868e', 'Nama Siswa 29', 'siswa'),
(190, '1010101039', 'e02548bbc98d306c60bbd841bc7052a2', 'Nama Siswa 30', 'siswa'),
(191, '1010101040', '611486a6582d9628eed06559966028aa', 'Nama Siswa 31', 'siswa'),
(192, '1010101041', '9e78246edc85c7a9c9d920189b85d802', 'Nama Siswa 32', 'siswa'),
(193, '1010101042', 'f1e072ccaeddb0277d636d8d1a3fafce', 'Nama Siswa 33', 'siswa'),
(194, '1010101043', '0ded2e7b6c9aaccd8873d36635d6fdc8', 'Nama Siswa 34', 'siswa'),
(195, '1010101044', '9be7b4ae84a51f8038734846c26992e5', 'Nama Siswa 35', 'siswa'),
(196, '1010101045', 'a9ed264e75515ee3def0d9566446bcb0', 'Nama Siswa 36', 'siswa'),
(197, '1010101046', '1765af0242ac60da20e58a777a269df2', 'Nama Siswa 37', 'siswa'),
(198, '1010101047', '9a2e6eb14805034cacce8ca35e977478', 'Nama Siswa 38', 'siswa'),
(199, '1010101048', '8ea3802706f79312a42a5d101957b1d4', 'Nama Siswa 39', 'siswa'),
(200, '1010101049', '2f6dd812498298891d19be078bea4fd9', 'Nama Siswa 40', 'siswa'),
(201, '1010101050', '1db9c378409434602b250afa58f37e41', 'Nama Siswa 41', 'siswa'),
(202, '1010101051', '93283215071d6fa7bf9f20562e7ce932', 'Nama Siswa 42', 'siswa'),
(203, '1010101052', '8c3819c97eae7c9e73ac4a0cbd2a05c0', 'Nama Siswa 43', 'siswa'),
(204, '1010101053', '34d5edd33ac542e7f7b4506312d420ab', 'Nama Siswa 44', 'siswa'),
(205, '1010101054', '152a70529144ea9fda7b97343f1b0c66', 'Nama Siswa 45', 'siswa'),
(206, '1010101055', 'c11020e3a96132df846e8b1597319787', 'Nama Siswa 46', 'siswa'),
(207, '1010101056', 'c8ceb13480b675f328b63c9c698fd3cb', 'Nama Siswa 47', 'siswa'),
(208, '1010101057', '99dbbbec23a943a21e37031292c4a396', 'Nama Siswa 48', 'siswa'),
(209, '1010101058', '0097c480c6e17217f37f3a633b484323', 'Nama Siswa 49', 'siswa'),
(210, '1010101059', '71f87f8529187fb077ea68c4fda6a510', 'Nama Siswa 50', 'siswa'),
(211, '1010101060', 'dcbf4ae773b6359a966a25782ab5df63', 'Nama Siswa 51', 'siswa'),
(212, '1010101061', 'c321b0c8f26024d9f80035d6470d8927', 'Nama Siswa 52', 'siswa'),
(213, '1010101062', '16d6ff1d9c6a5d615f60615b8dcd96ba', 'Nama Siswa 53', 'siswa'),
(214, '1010101063', '9826508b428cbf6843dd89cea76578ac', 'Nama Siswa 54', 'siswa'),
(215, '1010101064', '727e1e7bc411059e1b9786f90b94211a', 'Nama Siswa 55', 'siswa'),
(216, '1010101065', 'f7442a6783b519f569c4c6a1fe60581d', 'Nama Siswa 56', 'siswa'),
(217, '1010101066', '36d6ab1df987106b920ea9c12d5d9892', 'Nama Siswa 57', 'siswa'),
(218, '1010101067', 'd1b5716888dd7233b5a11ffa468cb943', 'Nama Siswa 58', 'siswa'),
(219, '1010101068', 'bad535e8b2b842c65f2cdf13838159a8', 'Nama Siswa 59', 'siswa'),
(220, '1010101069', '0d16698ccc74fb72f43d2fb8033e20c3', 'Nama Siswa 60', 'siswa'),
(221, '1010101070', '960ac0b892cb0e3808fcddb6199966ad', 'Nama Siswa 61', 'siswa'),
(222, '1010101071', '6327a4b6c3ee960d47ba89ccf0f005c6', 'Nama Siswa 62', 'siswa'),
(223, '1010101072', 'b69a397ce91c39972250152678f6474a', 'Nama Siswa 63', 'siswa'),
(224, '1010101073', '6030ff034e7c63a31bbace4f7a530a0b', 'Nama Siswa 64', 'siswa'),
(225, '1010101074', 'f07c27602e03ca5892f26f2d5ee7a0d1', 'Nama Siswa 65', 'siswa'),
(226, '1010101075', '3e63e0dedbff122972e1c3bd5b6916fe', 'Nama Siswa 66', 'siswa'),
(227, '1010101076', '01460bb2cbd75a6227aef8995b2d2171', 'Nama Siswa 67', 'siswa'),
(228, '1010101077', 'e76926b410aa5e6fd072c3c9d384d365', 'Nama Siswa 68', 'siswa'),
(229, '1010101078', '584c684408bfedecf8574655ace1999e', 'Nama Siswa 69', 'siswa'),
(230, '1010101079', 'f19ef8b5aff3646374bec5b9239667fe', 'Nama Siswa 70', 'siswa'),
(231, '1010101080', '2447dae8516cd87340f1e97bf9851693', 'Nama Siswa 71', 'siswa'),
(232, '1010101081', '4ff39a723026cd91c11c838e245ccd75', 'Nama Siswa 72', 'siswa'),
(233, '1010101082', '5c2686da8f72d5f5cda71b2fa0e5f024', 'Nama Siswa 73', 'siswa'),
(234, '1010101083', '84cbc6e3bc3d3130841f835c8fa12e07', 'Nama Siswa 74', 'siswa'),
(235, '1010101084', 'a2a9065b7e173544364254ad0e99c551', 'Nama Siswa 75', 'siswa'),
(236, '1010101085', 'e2253c63de3788e50a882fad9bfa4890', 'Nama Siswa 76', 'siswa'),
(237, '1010101086', '3611b5135a85650d7561966b52b168fa', 'Nama Siswa 77', 'siswa'),
(238, '1010101087', '8b1aa9b7173d7f163ec9edf3503723aa', 'Nama Siswa 78', 'siswa'),
(239, '1010101088', 'de36301082c8bfa76edb686c3bb53e35', 'Nama Siswa 79', 'siswa'),
(240, '1010101089', 'a3580eae7964daa2801f90787bbeb41e', 'Nama Siswa 80', 'siswa'),
(241, '1010101090', 'fbd3f1924f8ea0669e42b5647ce37537', 'Nama Siswa 81', 'siswa'),
(242, '1010101091', '9e24ad61c41bc5d03e800b6a21db8031', 'Nama Siswa 82', 'siswa'),
(243, '1010101092', '68d2e9be42ee6c518dda4269ed1b7e58', 'Nama Siswa 83', 'siswa'),
(244, '1010101093', '3aad69f076fe190c7d4b7d30b409058c', 'Nama Siswa 84', 'siswa'),
(245, '1010101094', '091409cfc1d85767447d4d72b07c8d74', 'Nama Siswa 85', 'siswa'),
(246, '1010101095', '7b67036413aa7620b0d0ab209f311a8a', 'Nama Siswa 86', 'siswa'),
(247, '1010101096', '8ad1c8609e4cba859ff3d88754e09a14', 'Nama Siswa 87', 'siswa'),
(248, '1010101097', 'c2ffca1163d2c5566ea0be03c7afb132', 'Nama Siswa 88', 'siswa'),
(249, '1010101098', '587731e9aa495bbde46408831b3f4914', 'Nama Siswa 89', 'siswa'),
(250, '1010101099', 'fc688b6ed4c01aca1c66c6752295c4aa', 'Nama Siswa 90', 'siswa'),
(251, '1010101100', '4fff1cffe6f27981f58781fdd595bd3b', 'Nama Siswa 91', 'siswa'),
(252, '1010101101', 'f23bea9d60850a03ca76e1cd7cb1996e', 'Nama Siswa 92', 'siswa'),
(253, '1010101102', 'b79ba62b492849693d9d129ff05dd357', 'Nama Siswa 93', 'siswa'),
(254, '1010101103', '2c5770646aa82d37fb4b2c9d4941e7b2', 'Nama Siswa 94', 'siswa'),
(255, '1010101104', '4fada29fa539162febe75b3c51d9755a', 'Nama Siswa 95', 'siswa'),
(256, '1010101105', '8676c0c5e454e8848bb65275a05b44bc', 'Nama Siswa 96', 'siswa'),
(257, '1010101106', '9436ab47c67c1fbbda31a5d2e87765ac', 'Nama Siswa 97', 'siswa'),
(258, '1010101107', '9786c8c86fbe3175475a876de934522a', 'Nama Siswa 98', 'siswa'),
(259, '1010101108', '95f2050c37504e1c35dc5a6a0fcbf16c', 'Nama Siswa 99', 'siswa'),
(260, '1010121109', '414cfd6737fde045c66afef7859754d1', 'Nama Siswa 100', 'siswa'),
(261, '9876543210', 'e388c1c5df4933fa01f6da9f92595589', 'Insan Kamil', 'siswa'),
(262, '198392717007091001', '98e162102c0b57eeb5f0dfa3a9932704', 'Adi, S.Pd., Gr', 'guru');

-- --------------------------------------------------------

--
-- Struktur dari tabel `wali_kelas`
--

CREATE TABLE `wali_kelas` (
  `id` int(11) NOT NULL,
  `kelas` varchar(20) NOT NULL,
  `nama_wali` varchar(100) NOT NULL,
  `nip_wali` varchar(50) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Dumping data untuk tabel `wali_kelas`
--

INSERT INTO `wali_kelas` (`id`, `kelas`, `nama_wali`, `nip_wali`, `created_at`) VALUES
(1, '7A', 'Adi, S.Pd., Gr', '198392717007091001', '2025-08-23 14:21:15');

--
-- Indexes for dumped tables
--

--
-- Indeks untuk tabel `absensi`
--
ALTER TABLE `absensi`
  ADD PRIMARY KEY (`id`),
  ADD KEY `siswa_id` (`siswa_id`);

--
-- Indeks untuk tabel `hari_libur`
--
ALTER TABLE `hari_libur`
  ADD PRIMARY KEY (`id`);

--
-- Indeks untuk tabel `jurnal_kebiasaan`
--
ALTER TABLE `jurnal_kebiasaan`
  ADD PRIMARY KEY (`id`);

--
-- Indeks untuk tabel `pelanggaran`
--
ALTER TABLE `pelanggaran`
  ADD PRIMARY KEY (`id`);

--
-- Indeks untuk tabel `pelanggaran_log`
--
ALTER TABLE `pelanggaran_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `pelanggaran_id` (`pelanggaran_id`);

--
-- Indeks untuk tabel `profil_sekolah`
--
ALTER TABLE `profil_sekolah`
  ADD PRIMARY KEY (`id`);

--
-- Indeks untuk tabel `siswa`
--
ALTER TABLE `siswa`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nisn` (`nisn`);

--
-- Indeks untuk tabel `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- Indeks untuk tabel `wali_kelas`
--
ALTER TABLE `wali_kelas`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT untuk tabel yang dibuang
--

--
-- AUTO_INCREMENT untuk tabel `absensi`
--
ALTER TABLE `absensi`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT untuk tabel `hari_libur`
--
ALTER TABLE `hari_libur`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT untuk tabel `jurnal_kebiasaan`
--
ALTER TABLE `jurnal_kebiasaan`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'Primary Key, Auto Increment', AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT untuk tabel `pelanggaran`
--
ALTER TABLE `pelanggaran`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT untuk tabel `pelanggaran_log`
--
ALTER TABLE `pelanggaran_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT untuk tabel `profil_sekolah`
--
ALTER TABLE `profil_sekolah`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT untuk tabel `siswa`
--
ALTER TABLE `siswa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT untuk tabel `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=263;

--
-- AUTO_INCREMENT untuk tabel `wali_kelas`
--
ALTER TABLE `wali_kelas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- Ketidakleluasaan untuk tabel pelimpahan (Dumped Tables)
--

--
-- Ketidakleluasaan untuk tabel `absensi`
--
ALTER TABLE `absensi`
  ADD CONSTRAINT `absensi_ibfk_1` FOREIGN KEY (`siswa_id`) REFERENCES `siswa` (`id`);

--
-- Ketidakleluasaan untuk tabel `pelanggaran_log`
--
ALTER TABLE `pelanggaran_log`
  ADD CONSTRAINT `pelanggaran_log_ibfk_1` FOREIGN KEY (`pelanggaran_id`) REFERENCES `pelanggaran` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
