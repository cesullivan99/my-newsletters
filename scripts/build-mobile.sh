#!/bin/bash

# Mobile App Build Script for My Newsletters Voice Assistant
# Builds iOS and Android apps for testing and release

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PLATFORM=${1:-both}  # ios, android, or both
BUILD_TYPE=${2:-debug}  # debug or release
FRONTEND_DIR="frontend"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}My Newsletters Mobile App Build${NC}"
echo -e "${GREEN}Platform: $PLATFORM${NC}"
echo -e "${GREEN}Build Type: $BUILD_TYPE${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Node.js is not installed${NC}"
        exit 1
    fi
    
    # Check npm/yarn
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}npm is not installed${NC}"
        exit 1
    fi
    
    # Platform-specific checks
    if [[ "$PLATFORM" == "ios" || "$PLATFORM" == "both" ]]; then
        if ! command -v xcodebuild &> /dev/null; then
            echo -e "${RED}Xcode is not installed (required for iOS)${NC}"
            exit 1
        fi
        
        if ! command -v pod &> /dev/null; then
            echo -e "${RED}CocoaPods is not installed (required for iOS)${NC}"
            echo "Install with: sudo gem install cocoapods"
            exit 1
        fi
    fi
    
    if [[ "$PLATFORM" == "android" || "$PLATFORM" == "both" ]]; then
        if [ -z "$ANDROID_HOME" ]; then
            echo -e "${RED}ANDROID_HOME is not set${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Prerequisites check passed${NC}"
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    
    cd $FRONTEND_DIR
    
    # Install npm packages
    npm install
    
    # Install iOS pods if building for iOS
    if [[ "$PLATFORM" == "ios" || "$PLATFORM" == "both" ]]; then
        echo -e "${YELLOW}Installing iOS pods...${NC}"
        cd ios
        pod install
        cd ..
    fi
    
    cd ..
    
    echo -e "${GREEN}Dependencies installed${NC}"
}

# Function to clean build artifacts
clean_build() {
    echo -e "${YELLOW}Cleaning previous builds...${NC}"
    
    cd $FRONTEND_DIR
    
    # Clean React Native cache
    npx react-native clean
    
    # Clean iOS build
    if [[ "$PLATFORM" == "ios" || "$PLATFORM" == "both" ]]; then
        cd ios
        xcodebuild clean
        rm -rf build
        cd ..
    fi
    
    # Clean Android build
    if [[ "$PLATFORM" == "android" || "$PLATFORM" == "both" ]]; then
        cd android
        ./gradlew clean
        cd ..
    fi
    
    cd ..
    
    echo -e "${GREEN}Build artifacts cleaned${NC}"
}

# Function to build iOS app
build_ios() {
    echo -e "${YELLOW}Building iOS app...${NC}"
    
    cd $FRONTEND_DIR
    
    if [ "$BUILD_TYPE" = "release" ]; then
        # Build release version
        npx react-native build-ios --mode=Release
        
        # Archive for App Store
        cd ios
        xcodebuild -workspace MyNewsletters.xcworkspace \
                  -scheme MyNewsletters \
                  -configuration Release \
                  -archivePath ./build/MyNewsletters.xcarchive \
                  archive
        
        # Export IPA
        xcodebuild -exportArchive \
                  -archivePath ./build/MyNewsletters.xcarchive \
                  -exportPath ./build \
                  -exportOptionsPlist ./exportOptions.plist
        
        cd ..
        
        echo -e "${GREEN}iOS release build complete: frontend/ios/build/MyNewsletters.ipa${NC}"
    else
        # Build debug version
        npx react-native run-ios --no-packager
        echo -e "${GREEN}iOS debug build complete${NC}"
    fi
    
    cd ..
}

# Function to build Android app
build_android() {
    echo -e "${YELLOW}Building Android app...${NC}"
    
    cd $FRONTEND_DIR
    
    if [ "$BUILD_TYPE" = "release" ]; then
        # Build release APK
        cd android
        ./gradlew assembleRelease
        
        # Build release bundle for Play Store
        ./gradlew bundleRelease
        
        cd ..
        
        echo -e "${GREEN}Android release build complete:${NC}"
        echo -e "${GREEN}  APK: frontend/android/app/build/outputs/apk/release/app-release.apk${NC}"
        echo -e "${GREEN}  Bundle: frontend/android/app/build/outputs/bundle/release/app-release.aab${NC}"
    else
        # Build debug version
        npx react-native run-android --no-packager
        echo -e "${GREEN}Android debug build complete${NC}"
    fi
    
    cd ..
}

# Function to start Metro bundler
start_metro() {
    echo -e "${YELLOW}Starting Metro bundler...${NC}"
    
    cd $FRONTEND_DIR
    npx react-native start --reset-cache &
    METRO_PID=$!
    cd ..
    
    # Wait for Metro to start
    sleep 5
    
    echo -e "${GREEN}Metro bundler started (PID: $METRO_PID)${NC}"
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running mobile app tests...${NC}"
    
    cd $FRONTEND_DIR
    
    # Run Jest tests
    npm test
    
    # Run linting
    npm run lint
    
    cd ..
    
    echo -e "${GREEN}Tests passed${NC}"
}

# Function to generate signing key (Android)
generate_android_signing() {
    echo -e "${YELLOW}Generating Android signing key...${NC}"
    
    cd $FRONTEND_DIR/android/app
    
    keytool -genkeypair -v \
            -storetype PKCS12 \
            -keystore my-newsletters-release.keystore \
            -alias my-newsletters \
            -keyalg RSA \
            -keysize 2048 \
            -validity 10000
    
    cd ../../../
    
    echo -e "${GREEN}Android signing key generated${NC}"
    echo -e "${YELLOW}Add the following to android/gradle.properties:${NC}"
    echo "MYAPP_RELEASE_STORE_FILE=my-newsletters-release.keystore"
    echo "MYAPP_RELEASE_KEY_ALIAS=my-newsletters"
    echo "MYAPP_RELEASE_STORE_PASSWORD=<your-password>"
    echo "MYAPP_RELEASE_KEY_PASSWORD=<your-password>"
}

# Main build flow
main() {
    check_prerequisites
    install_dependencies
    clean_build
    run_tests
    
    # Start Metro for debug builds
    if [ "$BUILD_TYPE" = "debug" ]; then
        start_metro
    fi
    
    # Build platforms
    if [[ "$PLATFORM" == "ios" || "$PLATFORM" == "both" ]]; then
        build_ios
    fi
    
    if [[ "$PLATFORM" == "android" || "$PLATFORM" == "both" ]]; then
        build_android
    fi
    
    # Kill Metro if started
    if [ ! -z "$METRO_PID" ]; then
        kill $METRO_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# Parse command for special operations
if [ "$1" = "sign-android" ]; then
    generate_android_signing
    exit 0
fi

# Run main build
main