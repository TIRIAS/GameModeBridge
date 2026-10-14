plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.gamemodebridge"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.gamemodebridge"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.serialization.json)
}

// JVM 단위 테스트가 PC와 같은 암호화 테스트 벡터 파일을 읽도록 경로를 전달함
tasks.withType<Test>().configureEach {
    val testVectors = rootProject.file("../shared/testvectors/crypto_v1.json")
    inputs.file(testVectors)
    systemProperty("gmb.testvectors", testVectors.absolutePath)
}
