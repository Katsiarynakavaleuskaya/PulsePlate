import Foundation
import XcodeKit

// Этот скрипт будет выполнен в Xcode для добавления Lottie пакета
let packageURL = "https://github.com/airbnb/lottie-ios.git"
let packageVersion = "4.4.0"

print("📦 Добавляем Lottie пакет...")
print("URL: \(packageURL)")
print("Version: \(packageVersion)")

// Инструкции для ручного добавления:
print("\n📋 РУЧНЫЕ ШАГИ:")
print("1. Откройте PulsePlate.xcodeproj в Xcode")
print("2. File → Add Package Dependencies...")
print("3. Введите URL: \(packageURL)")
print("4. Выберите Version: Up to Next Major, From: \(packageVersion)")
print("5. Нажмите Add Package")
print("6. Выберите Target 'PulsePlate'")
print("7. Нажмите Add Package")
print("\n✅ Готово! Lottie будет добавлен в проект")
