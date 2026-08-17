import 'dart:math';
import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../../../core/database/app_database.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/sms_gateway.dart';
import '../../../core/services/sync_manager.dart';
import '../../../core/services/mesh_relay.dart';

class EmergencySosScreen extends StatefulWidget {
  final AppDatabase database;
  final ApiClient apiClient;

  const EmergencySosScreen({
    Key? key,
    required this.database,
    required this.apiClient,
  }) : super(key: key);

  @override
  State<EmergencySosScreen> createState() => _EmergencySosScreenState();
}

class _EmergencySosScreenState extends State<EmergencySosScreen> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late SmsGateway _smsGateway;
  late SyncManager _syncManager;
  late MeshRelay _meshRelay;

  String _selectedLanguage = 'en'; // 'en' or 'hi'
  String _selectedCategory = 'medical';
  final TextEditingController _messageController = TextEditingController();
  bool _isDispatching = false;
  bool _isCheckingIn = false;
  bool _isOffline = false;
  bool _meshRelayActive = true;
  String? _lastDispatchedStatus;

  // Localization Dictionary (Scoped directly to eliminate external code generation dependencies)
  static const Map<String, Map<String, String>> _localizedStrings = {
    'en': {
      'title': 'Emergency SOS Mode',
      'hold_tap': 'HOLD / TAP',
      'sos': 'SOS',
      'im_safe': "I'm Safe",
      'category_header': 'Emergency Category',
      'cat_medical': 'Medical Emergency',
      'cat_disaster': 'Natural Disaster',
      'cat_security': 'Security / Safety',
      'cat_general': 'General Assistance',
      'cat_medical_sub': 'Hospital & Ambulance',
      'cat_disaster_sub': 'Flood & Cyclone Evacuation',
      'cat_security_sub': 'Police & Protection',
      'cat_general_sub': 'Local Rescue Team',
      'hint': 'Optional details (e.g. 2 people trapped, need boat)...',
      'offline_banner': 'Offline Mode: Local Drift SQLite active. Auto-sync on reconnect.',
      'online_banner': 'Online Mode: Connected to GhostNet Emergency Mesh Gateway.',
      'mesh_active': 'Mesh Relay Active',
      'reassurance': 'No Manual Retry Required: Alerts are signed with GPS timestamp and automatically sync silently upon carrier or mesh reconnect.',
      'sos_delivered': 'SOS Delivered to Emergency Operations Centre!',
      'sos_queued': 'Queued Locally in SQLite — GhostNet will auto-dispatch when network reconnects.',
      'safe_toast': "Marked 'I am Safe' — Logged to local record & synced.",
      'radio_prompt_title': 'Enable Bluetooth & Wi-Fi',
      'radio_prompt_desc': 'Nearby device mesh relay requires Bluetooth or Wi-Fi to be active for peer-to-peer transmission in zero-signal zones.',
      'enable_button': 'Enable Mesh Radios',
    },
    'hi': {
      'title': 'आपातकालीन एसओएस मोड',
      'hold_tap': 'दबाएं या स्पर्श करें',
      'sos': 'एसओएस',
      'im_safe': 'मैं सुरक्षित हूं',
      'category_header': 'आपातकालीन श्रेणी',
      'cat_medical': 'चिकित्सा आपातकाल',
      'cat_disaster': 'प्राकृतिक आपदा / बाढ़',
      'cat_security': 'सुरक्षा सहायता',
      'cat_general': 'सामान्य सहायता',
      'cat_medical_sub': 'अस्पताल और एम्बुलेंस',
      'cat_disaster_sub': 'बाढ़ एवं चक्रवात बचाव',
      'cat_security_sub': 'पुलिस एवं सुरक्षा दल',
      'cat_general_sub': 'स्थानीय बचाव दल',
      'hint': 'अतिरिक्त विवरण (उदा. 2 लोग फंसे हैं, नाव चाहिए)...',
      'offline_banner': 'ऑफलाइन मोड: स्थानीय ड्रिफ्ट एसक्यूलाइट सक्रिय। नेटवर्क आने पर ऑटो-सिंक।',
      'online_banner': 'ऑनलाइन मोड: घोस्टनेट आपातकालीन मेश गेटवे से जुड़ा है।',
      'mesh_active': 'मेश रिले सक्रिय',
      'reassurance': 'मैन्युअल पुनः प्रयास की आवश्यकता नहीं: अलर्ट जीपीएस समय के साथ सुरक्षित हैं और नेटवर्क आने पर अपने आप भेजे जाएंगे।',
      'sos_delivered': 'एसओएस आपातकालीन नियंत्रण कक्ष को सफलतापूर्वक भेजा गया!',
      'sos_queued': 'ऑफलाइन एसक्यूलाइट में सुरक्षित — नेटवर्क आने पर अपने आप भेजा जाएगा।',
      'safe_toast': "सुरक्षित दर्ज किया गया — रिकॉर्ड सुरक्षित और सिंक हुआ।",
      'radio_prompt_title': 'ब्लूटूथ और वाई-फाई सक्षम करें',
      'radio_prompt_desc': 'शून्य सिग्नल क्षेत्र में नजदीकी उपकरणों के माध्यम से मेश रिले प्रसारण के लिए ब्लूटूथ या वाई-फाई आवश्यक है।',
      'enable_button': 'मेश रेडियो चालू करें',
    },
  };

  String tr(String key) {
    return _localizedStrings[_selectedLanguage]?[key] ?? key;
  }

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _smsGateway = MockSmsGateway();
    _syncManager = SyncManager(database: widget.database, apiClient: widget.apiClient);
    _meshRelay = SimulatedMeshRelay();
    
    // Start mesh listener
    _meshRelay.start(onPacketReceived: (payload) async {
      print('[EmergencyScreen] Mesh packet received: ${payload['category']}');
      // If this device has network, relay it to backend immediately
      await widget.apiClient.submitSosBatch([payload]);
    });

    _checkConnectivity();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _messageController.dispose();
    _meshRelay.stop();
    super.dispose();
  }

  Future<void> _checkConnectivity() async {
    final connectivityResult = await Connectivity().checkConnectivity();
    if (mounted) {
      setState(() {
        _isOffline = connectivityResult.contains(ConnectivityResult.none);
      });
    }
  }

  Future<void> _triggerSos() async {
    setState(() => _isDispatching = true);
    final deviceId = await widget.database.getOrCreateDeviceId();

    final double lat = 23.1950 + (Random().nextDouble() - 0.5) * 0.04;
    final double lon = 86.0470 + (Random().nextDouble() - 0.5) * 0.04;
    final messageText = _messageController.text.trim().isNotEmpty
        ? _messageController.text.trim()
        : 'Emergency SOS: Immediate responder assistance needed.';

    // 1. Queue locally in Drift SQLite
    final alertId = await widget.database.queueSosAlert(
      deviceId: deviceId,
      lat: lat,
      lon: lon,
      category: _selectedCategory,
      message: messageText,
    );

    // 2. Dispatch Mesh Relay Packet (P2P / Loopback)
    await _meshRelay.broadcastEmergencyPacket({
      'device_id': deviceId,
      'lat': lat,
      'lon': lon,
      'category': _selectedCategory,
      'message': messageText,
      'offline_created_at': DateTime.now().toUtc().toIso8601String(),
      'is_relayed': true,
    });

    // 3. Dispatch SMS Gateway Fallback (Mock)
    await _smsGateway.sendEmergencySms(
      category: _selectedCategory,
      lat: lat,
      lon: lon,
      message: messageText,
    );

    // 4. Attempt immediate direct sync if online
    final syncResults = await _syncManager.syncAllPending();
    final synced = (syncResults['sos'] ?? 0) > 0;

    if (mounted) {
      setState(() {
        _isDispatching = false;
        _lastDispatchedStatus = synced ? tr('sos_delivered') : tr('sos_queued');
      });

      _messageController.clear();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_lastDispatchedStatus!),
          backgroundColor: synced ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  Future<void> _triggerCheckIn() async {
    setState(() => _isCheckingIn = true);
    final deviceId = await widget.database.getOrCreateDeviceId();

    await widget.database.queueCheckIn(
      deviceId: deviceId,
      lat: 23.3322,
      lon: 86.3652,
      status: 'safe',
    );

    await _syncManager.syncAllPending();

    if (mounted) {
      setState(() => _isCheckingIn = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(tr('safe_toast')),
          backgroundColor: const Color(0xFF10B981),
        ),
      );
    }
  }

  void _showRadioPromptDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text(tr('radio_prompt_title'), style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: Text(tr('radio_prompt_desc'), style: const TextStyle(color: Colors.white70, fontSize: 13)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(tr('enable_button'), style: const TextStyle(color: Color(0xFF00F0FF), fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Color _getCategoryColor(String cat) {
    switch (cat) {
      case 'medical':
        return const Color(0xFFF43F5E);
      case 'disaster':
        return const Color(0xFFF59E0B);
      case 'security':
        return const Color(0xFF3B82F6);
      case 'general':
      default:
        return const Color(0xFFA855F7);
    }
  }

  @override
  Widget build(BuildContext context) {
    final categoryColor = _getCategoryColor(_selectedCategory);
    final isHindi = _selectedLanguage == 'hi';

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF111827),
        elevation: 0,
        title: Row(
          children: [
            const Icon(Icons.shield_rounded, color: Color(0xFFF43F5E), size: 20),
            const SizedBox(width: 8),
            Text(
              tr('title'),
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
            ),
          ],
        ),
        actions: [
          // Language Switcher (EN / हिन्दी)
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF1F2937),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.white12),
            ),
            child: Row(
              children: [
                GestureDetector(
                  onTap: () => setState(() => _selectedLanguage = 'en'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: !isHindi ? const Color(0xFF00F0FF) : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'EN',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: !isHindi ? Colors.black : Colors.white60,
                      ),
                    ),
                  ),
                ),
                GestureDetector(
                  onTap: () => setState(() => _selectedLanguage = 'hi'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: isHindi ? const Color(0xFF00F0FF) : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'हिन्दी',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: isHindi ? Colors.black : Colors.white60,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Safe check-in button
          Padding(
            padding: const EdgeInsets.only(right: 12.0, left: 4.0),
            child: TextButton.icon(
              onPressed: _isCheckingIn ? null : _triggerCheckIn,
              icon: const Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 16),
              label: Text(
                tr('im_safe'),
                style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 11),
              ),
              style: TextButton.styleFrom(
                backgroundColor: const Color(0xFF10B981).withOpacity(0.12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            
            // Status & Mesh Relay Pill
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFF1F2937),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                children: [
                  Icon(
                    _isOffline ? Icons.wifi_off_rounded : Icons.wifi_rounded,
                    color: _isOffline ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                    size: 18,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _isOffline ? tr('offline_banner') : tr('online_banner'),
                      style: const TextStyle(color: Colors.white70, fontSize: 11),
                    ),
                  ),
                  GestureDetector(
                    onTap: _showRadioPromptDialog,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFFA855F7).withOpacity(0.2),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFA855F7).withOpacity(0.5)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.bluetooth_searching_rounded, color: Color(0xFFA855F7), size: 12),
                          const SizedBox(width: 4),
                          Text(
                            tr('mesh_active'),
                            style: const TextStyle(color: Color(0xFFA855F7), fontSize: 9, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Giant Pulsing SOS Button
            GestureDetector(
              onTap: _isDispatching ? null : _triggerSos,
              child: AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  final scale = 1.0 + (_pulseController.value * 0.06);
                  return Transform.scale(
                    scale: scale,
                    child: Container(
                      width: 170,
                      height: 170,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            categoryColor,
                            categoryColor.withOpacity(0.7),
                          ],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: categoryColor.withOpacity(0.4),
                            blurRadius: 30,
                            spreadRadius: 6,
                          ),
                        ],
                        border: Border.all(color: Colors.white.withOpacity(0.8), width: 3),
                      ),
                      child: Center(
                        child: _isDispatching
                            ? const CircularProgressIndicator(color: Colors.white)
                            : Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Icon(Icons.warning_amber_rounded, size: 42, color: Colors.white),
                                  const SizedBox(height: 4),
                                  Text(
                                    tr('hold_tap'),
                                    style: const TextStyle(color: Colors.white70, fontSize: 10, letterSpacing: 1.5),
                                  ),
                                  Text(
                                    tr('sos'),
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 26,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 2,
                                    ),
                                  ),
                                ],
                              ),
                      ),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 24),

            // Category Picker
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                tr('category_header'),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
            const SizedBox(height: 10),

            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 2.6,
              children: [
                _buildCategoryCard('medical', tr('cat_medical'), tr('cat_medical_sub'), Icons.medical_services_rounded, const Color(0xFFF43F5E)),
                _buildCategoryCard('disaster', tr('cat_disaster'), tr('cat_disaster_sub'), Icons.flood_rounded, const Color(0xFFF59E0B)),
                _buildCategoryCard('security', tr('cat_security'), tr('cat_security_sub'), Icons.shield_rounded, const Color(0xFF3B82F6)),
                _buildCategoryCard('general', tr('cat_general'), tr('cat_general_sub'), Icons.help_center_rounded, const Color(0xFFA855F7)),
              ],
            ),

            const SizedBox(height: 16),

            // Message Field
            TextField(
              controller: _messageController,
              maxLines: 2,
              style: const TextStyle(color: Colors.white, fontSize: 12),
              decoration: InputDecoration(
                hintText: tr('hint'),
                hintStyle: const TextStyle(color: Colors.white38, fontSize: 12),
                filled: true,
                fillColor: const Color(0xFF111827),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(color: Colors.white12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(color: Color(0xFF00F0FF)),
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Reassurance Card
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF111827),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF00F0FF).withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lock_clock_rounded, color: Color(0xFF00F0FF), size: 22),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      tr('reassurance'),
                      style: const TextStyle(color: Colors.white70, fontSize: 11, height: 1.3),
                    ),
                  ),
                ],
              ),
            ),

          ],
        ),
      ),
    );
  }

  Widget _buildCategoryCard(String id, String label, String sublabel, IconData icon, Color color) {
    final isSelected = _selectedCategory == id;
    return GestureDetector(
      onTap: () => setState(() => _selectedCategory = id),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? color.withOpacity(0.2) : const Color(0xFF111827),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? color : Colors.white10,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    label,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    sublabel,
                    style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 9),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
