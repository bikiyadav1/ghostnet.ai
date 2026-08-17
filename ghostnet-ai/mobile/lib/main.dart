import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'src/core/database/app_database.dart';
import 'src/core/network/api_client.dart';
import 'src/features/coverage_map/presentation/coverage_map_screen.dart';
import 'src/features/emergency_sos/presentation/emergency_sos_screen.dart';
import 'src/features/safety_tips/presentation/safety_tips_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final database = AppDatabase();
  final apiClient = ApiClient();

  // Pre-initialize anonymous device ID in local storage
  await database.getOrCreateDeviceId();

  runApp(
    ProviderScope(
      child: GhostNetApp(
        database: database,
        apiClient: apiClient,
      ),
    ),
  );
}

class GhostNetApp extends StatelessWidget {
  final AppDatabase database;
  final ApiClient apiClient;

  const GhostNetApp({
    Key? key,
    required this.database,
    required this.apiClient,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GhostNet AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0B0F19),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00F0FF),
          secondary: Color(0xFF10B981),
          surface: Color(0xFF111827),
        ),
        fontFamily: 'Roboto',
      ),
      home: MainShellScreen(
        database: database,
        apiClient: apiClient,
      ),
    );
  }
}

class MainShellScreen extends StatefulWidget {
  final AppDatabase database;
  final ApiClient apiClient;

  const MainShellScreen({
    Key? key,
    required this.database,
    required this.apiClient,
  }) : super(key: key);

  @override
  State<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends State<MainShellScreen> {
  int _currentIndex = 0;

  late final List<Widget> _screens;

  @override
  void initState() {
    super.initState();
    _screens = [
      CoverageMapScreen(
        database: widget.database,
        apiClient: widget.apiClient,
      ),
      EmergencySosScreen(
        database: widget.database,
        apiClient: widget.apiClient,
      ),
      const SafetyTipsScreen(),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: const Color(0xFF111827),
          indicatorColor: const Color(0xFF00F0FF).withOpacity(0.2),
          labelTextStyle: MaterialStateProperty.all(
            const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.white70),
          ),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.map_rounded, color: Colors.white60),
              selectedIcon: Icon(Icons.map_rounded, color: Color(0xFF00F0FF)),
              label: 'Coverage',
            ),
            NavigationDestination(
              icon: Icon(Icons.emergency_rounded, color: Color(0xFFF43F5E)),
              selectedIcon: Icon(Icons.emergency_rounded, color: Color(0xFFF43F5E)),
              label: 'SOS Mode',
            ),
            NavigationDestination(
              icon: Icon(Icons.health_and_safety_rounded, color: Colors.white60),
              selectedIcon: Icon(Icons.health_and_safety_rounded, color: Color(0xFF10B981)),
              label: 'Safety Tips',
            ),
          ],
        ),
      ),
    );
  }
}
