import SwiftUI

struct LaunchScreenView: View {
    var body: some View {
        ZStack {
            Color("Navy")
                .ignoresSafeArea()
            VStack {
                Image("FitChef")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 180, height: 180)
                Text("PulsePlate")
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.top, 16)
            }
        }
    }
}

#Preview {
    LaunchScreenView()
}
