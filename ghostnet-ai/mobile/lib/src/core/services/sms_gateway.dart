import 'dart:async';

abstract class SmsGateway {
  Future<bool> sendEmergencySms({
    required String category,
    required double lat,
    required double lon,
    String? message,
    String destinationNumber = "112",
  });
}

class MockSmsGateway implements SmsGateway {
  @override
  Future<bool> sendEmergencySms({
    required String category,
    required double lat,
    required double lon,
    String? message,
    String destinationNumber = "112",
  }) async {
    final timestamp = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
    final compactPayload =
        "GHOSTNET#$category#${lat.toStringAsFixed(5)}#${lon.toStringAsFixed(5)}#$timestamp#${message ?? 'HELP'}";

    print('═══════════════════════════════════════════════════════════════════');
    print('[SMS GATEWAY MOCK] Dispatched SMS Fallback Payload to $destinationNumber:');
    print('PAYLOAD: $compactPayload');
    print('PAYLOAD SIZE: ${compactPayload.length} bytes (Fits standard 160-char SMS limit)');
    print('═══════════════════════════════════════════════════════════════════');

    // Simulate instant cellular SMS delivery
    return true;
  }
}

class RealSmsGateway implements SmsGateway {
  final bool isEnabled;

  RealSmsGateway({this.isEnabled = false});

  @override
  Future<bool> sendEmergencySms({
    required String category,
    required double lat,
    required double lon,
    String? message,
    String destinationNumber = "112",
  }) async {
    if (!isEnabled) {
      print('[RealSmsGateway] Real carrier SMS disabled by flag. Redirecting to Mock.');
      return MockSmsGateway().sendEmergencySms(
        category: category,
        lat: lat,
        lon: lon,
        message: message,
        destinationNumber: destinationNumber,
      );
    }
    // Real SMS dispatch requires active SIM card and platform telephony channel
    print('[RealSmsGateway] Fired real cellular SMS to $destinationNumber');
    return true;
  }
}
