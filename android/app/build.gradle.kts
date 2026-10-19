import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.google.services)
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

    // 릴리스 서명: android/keystore.properties(커밋 제외)가 있을 때만 서명함. 서명 키는 저장소 밖에 둠
    val keystoreProps = rootProject.file("keystore.properties")
    val releaseSigning = if (keystoreProps.exists()) {
        val props = Properties().apply { keystoreProps.inputStream().use { load(it) } }
        signingConfigs.create("release") {
            storeFile = file(props.getProperty("storeFile"))
            storePassword = props.getProperty("storePassword")
            keyAlias = props.getProperty("keyAlias")
            keyPassword = props.getProperty("keyPassword")
        }
    } else null

    buildTypes {
        release {
            signingConfig = releaseSigning
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
    implementation(libs.kotlinx.serialization.json)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
    implementation(libs.play.services.code.scanner)
    testImplementation(libs.junit)
}

// JVM 단위 테스트가 PC와 같은 암호화 테스트 벡터 파일을 읽도록 경로를 전달함
tasks.withType<Test>().configureEach {
    val testVectors = rootProject.file("../shared/testvectors/crypto_v1.json")
    inputs.file(testVectors)
    systemProperty("gmb.testvectors", testVectors.absolutePath)
}
