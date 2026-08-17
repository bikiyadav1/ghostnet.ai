import 'dart:math';
import 'package:geolocator/geolocator.dart';
import '../database/app_database.dart';

class LocationSignalSampler {
  final AppDatabase database;

  LocationSignalSampler({required this.database});

  // Capture current sample and persist to local Drift SQLite database
  Future<bool> sampleAndStore() async {
    try {
      final deviceId = await database.getOrCreateDeviceId();
      Position? position;

      try {
        LocationPermission permission = await Geolocator.checkPermission();
        if (permission == LocationPermission.denied) {
          permission = await Geolocator.requestPermission();
        }
        if (permission == LocationPermission.whileInUse ||
            permission == LocationPermission.always) {
          position = await Geolocator.getCurrentPosition(
            desiredAccuracy: LocationAccuracy.medium,
            timeLimit: const Duration(seconds: 4),
          );
        }
      } catch (e) {
        print('[Sampler] Location capture exception: $e');
      }

      // Fallback location for demo in Purulia if GPS not active on emulator
      final double lat = position?.latitude ?? (23.3322 + (Random().nextDouble() - 0.5) * 0.05);
      final double lon = position?.longitude ?? (86.3652 + (Random().nextDouble() - 0.5) * 0.05);

      // Simulated telephony signal measurement
      final int signalDbm = -75 + (Random().nextInt(40) - 20);
      final String networkType = signalDbm > -85 ? '4G' : signalDbm > -105 ? '3G' : '2G';

      await database.insertReading(
        deviceId: deviceId,
        lat: lat,
        lon: lon,
        networkType: networkType,
        signalDbm: signalDbm,
        downloadMbps: networkType == '4G' ? 24.5 : 3.2,
        uploadMbps: networkType == '4G' ? 8.1 : 1.1,
        latency_ms: networkType == '4G' ? 38 : 120,
        recordedAt: DateTime.now().toUtc(),
      );

      print('[Sampler] Recorded telemetry: $signalDbm dBm at ($lat, $lon)');
      return true;
    } catch (e) {
      print('[Sampler] Failed to sample and store: $e');
      return false;
    }
  }
}
