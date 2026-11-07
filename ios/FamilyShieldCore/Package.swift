// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "FamilyShieldCore",
    products: [
        .library(name: "FamilyShieldCore", targets: ["FamilyShieldCore"]),
    ],
    targets: [
        .target(name: "FamilyShieldCore"),
        .testTarget(name: "FamilyShieldCoreTests", dependencies: ["FamilyShieldCore"]),
    ]
)
